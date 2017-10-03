# -*- encoding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.exceptions import UnRetryableRequestError
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IContentBehavior
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IValueToJson
from guillotina.schema import Object
from guillotina.schema.fieldproperty import FieldProperty
from guillotina.utils import get_content_path
from guillotina.utils import import_class
from guillotina.utils import to_str
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface

import asyncio
import base64
import logging
import mimetypes
import os
import uuid


logger = logging.getLogger('guillotina')


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


@implementer(ICloudFileField)
class CloudFileField(Object):
    """
    A cloud file hosted file.

    Its configured on config.json with :

    "cloud_storage": "pserver.s3storage.interfaces.IS3FileField"

    or

    "cloud_storage": "pserver.gcloudstorage.interfaces.IGCloudFileField"

    """

    schema = IFile

    def __init__(self, **kw):
        super(CloudFileField, self).__init__(schema=self.schema, **kw)


@configure.adapter(
    for_=(IResource, IRequest, ICloudFileField),
    provides=IFileManager)
class CloudFileManager(object):

    def __init__(self, context, request, field):
        iface = import_class(app_settings['cloud_storage'])
        alsoProvides(field, iface)
        self.real_file_manager = getMultiAdapter(
            (context, request, field), IFileManager)

    async def download(self, *args, **kwargs):
        return await self.real_file_manager.download(*args, **kwargs)

    async def tus_options(self, *args, **kwargs):
        return await self.real_file_manager.tus_options(*args, **kwargs)

    async def tus_head(self, *args, **kwargs):
        return await self.real_file_manager.tus_head(*args, **kwargs)

    async def tus_patch(self, *args, **kwargs):
        return await self.real_file_manager.tus_patch(*args, **kwargs)

    async def tus_create(self, *args, **kwargs):
        return await self.real_file_manager.tus_create(*args, **kwargs)

    async def upload(self, *args, **kwargs):
        return await self.real_file_manager.upload(*args, **kwargs)

    async def iter_data(self, *args, **kwargs):
        async for chunk in self.real_file_manager.iter_data(*args, **kwargs):
            yield chunk

    async def save_file(self, generator, *args, **kwargs):
        return await self.real_file_manager.save_file(generator, *args, **kwargs)


@configure.adapter(for_=IFile, provides=IValueToJson)
def json_converter(value):
    if value is None:
        return value

    return {
        'filename': value.filename,
        'content_type': to_str(value.content_type),
        'size': value.size,
        'extension': value.extension,
        'md5': value.md5
    }


MAXCHUNKSIZE = 1 << 16
MAX_REQUEST_CACHE_SIZE = 6 * 1024 * 1024


async def read_request_data(request, chunk_size):
    '''
    cachable request data reader to help with conflict error requests
    '''
    if getattr(request, '_retry_attempt', 0) > 0:
        # we are on a retry request, see if we have read cached data yet...
        if request._retry_attempt > getattr(request, '_last_cache_data_retry_count', 0):
            if request._cache_data is None:
                # request payload was too large to fit into request cache.
                # so retrying this request is not supported and we need to throw
                # another error
                raise UnRetryableRequestError()
            data = request._cache_data[request._last_read_pos:request._last_read_pos + chunk_size]
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


@implementer(IFile)
class BaseCloudFile:
    """Base cloud file storage class"""

    filename = FieldProperty(IFile['filename'])

    def __init__(self, content_type='application/octet-stream',
                 filename=None, size=0, md5=None):
        if not isinstance(content_type, bytes):
            content_type = content_type.encode('utf8')
        self.content_type = content_type
        if filename is not None:
            self.filename = filename
            extension_discovery = filename.split('.')
            if len(extension_discovery) > 1:
                self._extension = extension_discovery[-1]
        elif self.filename is None:
            self.filename = uuid.uuid4().hex

        self._size = size
        self._md5 = md5
        self._data = b''

    def guess_content_type(self):
        ct = to_str(self.content_type)
        if ct == 'application/octet-stream':
            # try guessing content_type
            ct, _ = mimetypes.guess_type(self.filename)
            if ct is None:
                ct = 'application/octet-stream'
        return ct

    def generate_key(self, request, context):
        return '{}{}/{}::{}'.format(
            request._container_id,
            get_content_path(context),
            context._p_oid,
            uuid.uuid4().hex)

    def get_actual_size(self):
        return self._current_upload

    def _set_data(self, data):
        self._data = data

    def _get_data(self):
        return self._data

    data = property(_get_data, _set_data)

    @property
    def uri(self):
        if hasattr(self, '_uri'):
            return self._uri

    @property
    def size(self):
        if hasattr(self, '_size'):
            return self._size
        else:
            return None

    @property
    def md5(self):
        if hasattr(self, '_md5'):
            return self._md5
        else:
            return None

    @property
    def extension(self):
        if hasattr(self, '_extension'):
            return self._extension
        else:
            return None

    async def copy_cloud_file(self, new_uri):
        raise NotImplemented()

    async def rename_cloud_file(self, new_uri):
        raise NotImplemented()

    async def init_upload(self, context):
        raise NotImplemented()

    async def append_data(self, data):
        raise NotImplemented()

    async def finish_upload(self, context):
        raise NotImplemented()

    async def delete_upload(self, uri=None):
        raise NotImplemented()

    async def download(self, buf):
        raise NotImplemented()


def convert_base64_to_binary(b64data):
    prefix, _, b64data = b64data.partition(',')
    content_type = prefix.replace('data:', '').replace(';base64', '')
    data = base64.b64decode(b64data)
    return {
        'content_type': content_type,
        'data': data
    }


@configure.adapter(
    for_=(str, ICloudFileField),
    provides=IJSONToValue)
class CloudFileStrDeserializeValue:

    def __init__(self, value, field):
        self.value = convert_base64_to_binary(value)
        self.field = field

    async def generator(self):
        yield self.value['data']

    async def __call__(self, context, request):
        if IContentBehavior.implementedBy(context.__class__):
            field = self.field.bind(context)
            context = context.context
        else:
            field = self.field.bind(context)
        file_manager = getMultiAdapter((context, request, field), IFileManager)
        val = await file_manager.save_file(
            self.generator, content_type=self.value['content_type'],
            size=len(self.value['data']))
        return val
