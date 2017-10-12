# -*- encoding: utf-8 -*-
from aiohttp.web import StreamResponse
from aiohttp.web_exceptions import HTTPNotFound
from datetime import timedelta
from guillotina import configure
from guillotina._settings import app_settings
from guillotina.browser import Response
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

import asyncio
import base64
import logging
import mimetypes
import os
import uuid


logger = logging.getLogger('guillotina')

CHUNK_SIZE = 1024 * 1024 * 5
MAX_RETRIES = 5


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

    "cloud_storage": "guillotina.interfaces.IS3FileField"

    or

    "cloud_storage": "guillotina_gcloudstorage.interfaces.IGCloudFileField"

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
            if getattr(request, '_cache_data', None) is None:
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
    valid = True

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


class FileManagerUtility:

    file_class = None

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

    async def upload(self):
        """In order to support TUS and IO upload.

        we need to provide an upload that concats the incoming
        """
        self.context._p_register()  # writing to object

        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class):
            file = self.file_class(content_type=self.request.content_type)
            self.field.set(self.field.context or self.context, file)
            # Its a long transaction, savepoint
            # trns = get_transaction(self.request)
            # XXX no savepoint support right now?
        if 'X-UPLOAD-MD5HASH' in self.request.headers:
            file._md5 = self.request.headers['X-UPLOAD-MD5HASH']
        else:
            file._md5 = None

        if 'X-UPLOAD-EXTENSION' in self.request.headers:
            file._extension = self.request.headers['X-UPLOAD-EXTENSION']
        else:
            file._extension = None

        if 'X-UPLOAD-SIZE' in self.request.headers:
            file._size = int(self.request.headers['X-UPLOAD-SIZE'])
        else:
            raise AttributeError('x-upload-size header needed')

        if 'X-UPLOAD-FILENAME' in self.request.headers:
            file.filename = self.request.headers['X-UPLOAD-FILENAME']
        elif 'X-UPLOAD-FILENAME-B64' in self.request.headers:
            file.filename = base64.b64decode(
                self.request.headers['X-UPLOAD-FILENAME-B64']).decode("utf-8")
        else:
            file.filename = uuid.uuid4().hex

        await file.init_upload(self.context)
        self.request._last_read_pos = 0
        data = await read_request_data(self.request, CHUNK_SIZE)

        count = 0
        while data:
            old_current_upload = file._current_upload
            resp = await file.append_data(data)
            readed_bytes = file._current_upload - old_current_upload

            data = data[readed_bytes:]

            bytes_to_read = readed_bytes

            if resp.status in [200, 201]:
                break
            if resp.status == 308:
                count = 0
                data = await read_request_data(self.request, bytes_to_read)

            else:
                count += 1
                if count > MAX_RETRIES:
                    raise AttributeError('MAX retries error')
        # Test resp and checksum to finish upload
        await file.finish_upload(self.context)

    async def tus_create(self):
        self.context._p_register()  # writing to object

        # This only happens in tus-java-client, redirect this POST to a PATCH
        if self.request.headers.get('X-HTTP-Method-Override') == 'PATCH':
            return await self.tus_patch()

        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class):
            file = self.file_class(content_type=self.request.content_type)
            self.field.set(self.field.context or self.context, file)
        if 'CONTENT-LENGTH' in self.request.headers:
            file._current_upload = int(self.request.headers['CONTENT-LENGTH'])
        else:
            file._current_upload = 0
        if 'UPLOAD-LENGTH' in self.request.headers:
            file._size = int(self.request.headers['UPLOAD-LENGTH'])
        else:
            raise AttributeError('We need upload-length header')

        if 'UPLOAD-MD5' in self.request.headers:
            file._md5 = self.request.headers['UPLOAD-MD5']

        if 'UPLOAD-EXTENSION' in self.request.headers:
            file._extension = self.request.headers['UPLOAD-EXTENSION']

        if 'TUS-RESUMABLE' not in self.request.headers:
            raise AttributeError('Its a TUS needs a TUS version')

        if 'UPLOAD-METADATA' not in self.request.headers:
            file.filename = uuid.uuid4().hex
        else:
            filename = self.request.headers['UPLOAD-METADATA']
            file.filename = base64.b64decode(filename.split()[1]).decode('utf-8')

        await file.init_upload(self.context)
        # Location will need to be adapted on aiohttp 1.1.x
        resp = Response(headers={
            'Location': IAbsoluteURL(self.context, self.request)() + '/@tusupload/' + self.field.__name__,  # noqa
            'Tus-Resumable': '1.0.0',
            'Access-Control-Expose-Headers': 'Location,Tus-Resumable'
        }, status=201)
        return resp

    async def tus_patch(self):
        self.context._p_register()  # writing to object
        file = self.field.get(self.field.context or self.context)
        if 'CONTENT-LENGTH' in self.request.headers:
            to_upload = int(self.request.headers['CONTENT-LENGTH'])
        else:
            raise AttributeError('No content-length header')

        if 'UPLOAD-OFFSET' in self.request.headers:
            file._current_upload = int(self.request.headers['UPLOAD-OFFSET'])
        else:
            raise AttributeError('No upload-offset header')

        self.request._last_read_pos = 0
        data = await read_request_data(self.request, to_upload)

        count = 0
        while data:
            old_current_upload = file._current_upload
            resp = await file.append_data(data)
            # The amount of bytes that are readed
            if resp.status in [200, 201]:
                # If we finish the current upload is the size of the file
                readed_bytes = file._current_upload - old_current_upload
            else:
                # When it comes from gcloud the current_upload is one number less
                readed_bytes = file._current_upload - old_current_upload + 1

            # Cut the data so there is only the needed data
            data = data[readed_bytes:]

            bytes_to_read = len(data)

            if resp.status in [200, 201]:
                # If we are finished lets close it
                await file.finish_upload(self.context)
                data = None

            if bytes_to_read == 0:
                # We could read all the info
                break

            if bytes_to_read < 262144:
                # There is no enough data to send to gcloud
                break

            if resp.status in [400]:
                # Some error
                break

            if resp.status == 308:
                # We continue resumable
                count = 0
                data = await read_request_data(self.request, bytes_to_read)

            else:
                count += 1
                if count > MAX_RETRIES:
                    raise AttributeError('MAX retries error')
        expiration = file._resumable_uri_date + timedelta(days=7)

        resp = Response(headers={
            'Upload-Offset': str(file.get_actual_size()),
            'Tus-Resumable': '1.0.0',
            'Upload-Expires': expiration.isoformat(),
            'Access-Control-Expose-Headers': 'Upload-Offset,Upload-Expires,Tus-Resumable'
        })
        return resp

    async def tus_head(self):
        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class):
            raise KeyError('No file on this context')
        head_response = {
            'Upload-Offset': str(file.get_actual_size()),
            'Tus-Resumable': '1.0.0',
            'Access-Control-Expose-Headers': 'Upload-Offset,Upload-Length,Tus-Resumable'
        }
        if file.size:
            head_response['Upload-Length'] = str(file._size)
        resp = Response(headers=head_response)
        return resp

    async def tus_options(self):
        resp = Response(headers={
            'Tus-Resumable': '1.0.0',
            'Tus-Version': '1.0.0',
            'Tus-Max-Size': '1073741824',
            'Tus-Extension': 'creation,expiration'
        })
        return resp

    async def download(self, disposition=None):
        if disposition is None:
            disposition = self.request.GET.get('disposition', 'attachment')
        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class) or not file.valid:
            return HTTPNotFound(text='No file found')

        cors_renderer = app_settings['cors_renderer'](self.request)
        headers = await cors_renderer.get_headers()
        headers.update({
            'CONTENT-DISPOSITION': f'{disposition}; filename="%s"' % file.filename
        })

        download_resp = StreamResponse(headers=headers)
        download_resp.content_type = file.guess_content_type()
        if file.size:
            download_resp.content_length = file.size

        return await file.download(self.context, self.request)

    async def iter_data(self):
        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class) or file.uri is None:
            raise AttributeError('No field value')

        async for chunk in file.iter_data(self.context, self.request):
            yield chunk

    async def save_file(self, generator, content_type=None, size=None,
                        filename=None):
        self.context._p_register()  # writing to object

        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class):
            file = self.file_class(content_type=content_type)
            self.field.set(self.field.context or self.context, file)

        file._size = size
        if filename is None:
            filename = uuid.uuid4().hex
        file.filename = filename

        await file.init_upload(self.context)

        async for data in generator():
            await file.append_data(data)

        await file.finish_upload(self.context)
        return file
