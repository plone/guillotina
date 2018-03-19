from .const import MAX_REQUEST_CACHE_SIZE
from guillotina.exceptions import UnRetryableRequestError
from guillotina.utils import get_content_path
from guillotina.utils import to_str

import asyncio
import base64
import mimetypes
import os
import uuid


async def read_request_data(request, chunk_size):
    '''
    cachable request data reader to help with conflict error requests
    '''
    if getattr(request, '_retry_attempt', 0) > 0:
        # we are on a retry request, see if we have read cached data yet...
        if request._retry_attempt > getattr(request, '_last_cache_data_retry_count', 0):
            if getattr(request, '_cache_data', None) is None:
                # request payload was too large to fit into request cache.
                # so retrying this request is not supported and we need to throw
                # another error
                raise UnRetryableRequestError()
            start = request._last_read_pos
            end = request._last_read_pos + chunk_size
            data = request._cache_data[start:end]
            request._last_read_pos += len(data)
            if request._last_read_pos >= len(request._cache_data):
                # done reading cache data
                request._last_cache_data_retry_count = request._retry_attempt
            return data

    if not hasattr(request, '_cache_data'):
        request._cache_data = b''

    try:
        data = await request.content.readexactly(chunk_size)
    except asyncio.IncompleteReadError as e:
        data = e.partial

    if request._cache_data is not None:
        if len(request._cache_data) + len(data) > MAX_REQUEST_CACHE_SIZE:
            # we only allow caching up to chunk size, otherwise, no cache data..
            request._cache_data = None
        else:
            request._cache_data += data

    request._last_read_pos += len(data)
    return data


def get_contenttype(
        file=None,
        filename=None,
        default='application/octet-stream'):
    """Get the MIME content type of the given file and/or filename.
    """

    file_type = getattr(file, 'content_type', None)
    if file_type:
        return file_type

    filename = getattr(file, 'filename', filename)
    if filename:
        extension = os.path.splitext(filename)[1].lower()
        return mimetypes.types_map.get(extension, 'application/octet-stream')

    return default


def convert_base64_to_binary(b64data):
    prefix, _, b64data = b64data.partition(',')
    content_type = prefix.replace('data:', '').replace(';base64', '')
    data = base64.b64decode(b64data)
    return {
        'content_type': content_type,
        'data': data
    }


def guess_content_type(content_type, filename):
    ct = to_str(content_type)
    if not ct or ct == 'application/octet-stream':
        if not filename:
            return 'application/octet-stream'
        # try guessing content_type
        ct, _ = mimetypes.guess_type(filename)
        if ct is None:
            ct = 'application/octet-stream'
    return ct


def generate_key(request, context):
    return '{}{}/{}::{}'.format(
        request._container_id,
        get_content_path(context),
        context._p_oid,
        uuid.uuid4().hex)
