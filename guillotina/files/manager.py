#
# Upload file management structure
#
#  - File Manager(upload, download, tus)
#  - File data manager(size, content type, filename, current length, etc)
#  - File storage manager(db, s3, gcloud, etc)
#
from .const import CHUNK_SIZE
from aiohttp.web import StreamResponse
from datetime import datetime
from datetime import timedelta
from dateutil.tz import tzutc
from guillotina import configure
from guillotina._settings import app_settings
from guillotina.browser import Response
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.files.utils import read_request_data
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IFileStorageManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IUploadDataManager
from guillotina.utils import import_class
from zope.interface import alsoProvides

import base64
import uuid


@configure.adapter(
    for_=(IResource, IRequest, ICloudFileField),
    provides=IFileManager)
class CloudFileManager(object):

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

        iface = import_class(app_settings['cloud_storage'])
        alsoProvides(field, iface)

        self.file_storage_manager = get_multi_adapter(
            (context, request, field), IFileStorageManager)
        self.dm = get_adapter(
            self.file_storage_manager, IUploadDataManager)

    async def download(self, disposition=None):
        await self.dm.load()

        if disposition is None:
            disposition = self.request.GET.get('disposition', 'attachment')

        cors_renderer = app_settings['cors_renderer'](self.request)
        headers = await cors_renderer.get_headers()
        headers.update({
            'CONTENT-DISPOSITION': f'{disposition}; filename="%s"' % self.dm.get('filename')
        })

        download_resp = StreamResponse(headers=headers)
        download_resp.content_type = self.dm.get('content_type')
        if self.dm.get('size'):
            download_resp.content_length = self.dm.get('size')

        await download_resp.prepare(self.request)

        async for chunk in self.file_storage_manager.iter_data(self.dm):
            download_resp.write(chunk)
            await download_resp.drain()
        return download_resp

    async def tus_options(self, *args, **kwargs):
        resp = Response(headers={
            'Tus-Resumable': '1.0.0',
            'Tus-Version': '1.0.0',
            'Tus-Max-Size': '1073741824',
            'Tus-Extension': 'creation,expiration'
        })
        return resp

    async def tus_head(self, *args, **kwargs):
        await self.dm.load()
        head_response = {
            'Upload-Offset': str(self.dm.get_offset()),
            'Tus-Resumable': '1.0.0',
            'Access-Control-Expose-Headers': 'Upload-Offset,Upload-Length,Tus-Resumable'
        }
        if self.dm.get('size'):
            head_response['Upload-Length'] = str(self.dm.get('size'))
        resp = Response(headers=head_response)
        return resp

    async def tus_patch(self, *args, **kwargs):
        await self.dm.load()
        if 'CONTENT-LENGTH' in self.request.headers:
            to_upload = int(self.request.headers['CONTENT-LENGTH'])
        else:
            raise AttributeError('No content-length header')

        if 'UPLOAD-OFFSET' in self.request.headers:
            current_upload = int(self.request.headers['UPLOAD-OFFSET'])
        else:
            raise AttributeError('No upload-offset header')

        if current_upload != self.dm.get('current_upload'):
            raise AttributeError('Current upload does not match offset')

        self.request._last_read_pos = 0
        data = await read_request_data(self.request, to_upload)

        count = 0
        while data:
            count += len(data)
            await self.file_storage_manager.append(self.dm, data)
            data = await read_request_data(self.request, CHUNK_SIZE)

        resumable_uri_date = self.dm.get('resumable_uri_date')
        expiration = resumable_uri_date + timedelta(days=1)
        await self.dm.update(
            resumable_uri_date=expiration,
            current_upload=current_upload + count)

        if self.dm.get_offset() >= self.dm.get('size'):
            await self.file_storage_manager.finish(self.dm)
            await self.dm.finish()

        resp = Response(headers={
            'Upload-Offset': str(self.dm.get_offset()),
            'Tus-Resumable': '1.0.0',
            'Upload-Expires': expiration.isoformat(),
            'Access-Control-Expose-Headers': 'Upload-Offset,Upload-Expires,Tus-Resumable'
        })
        return resp

    async def tus_create(self, *args, **kwargs):
        await self.dm.load()
        # This only happens in tus-java-client, redirect this POST to a PATCH
        if self.request.headers.get('X-HTTP-Method-Override') == 'PATCH':
            return await self.tus_patch()

        current_upload = 0
        md5 = extension = size = None
        if 'CONTENT-LENGTH' in self.request.headers:
            current_upload = int(self.request.headers['CONTENT-LENGTH'])

        if 'UPLOAD-LENGTH' in self.request.headers:
            size = int(self.request.headers['UPLOAD-LENGTH'])
        else:
            raise AttributeError('We need upload-length header')

        if 'UPLOAD-MD5' in self.request.headers:
            md5 = self.request.headers['UPLOAD-MD5']

        if 'UPLOAD-EXTENSION' in self.request.headers:
            extension = self.request.headers['UPLOAD-EXTENSION']

        if 'TUS-RESUMABLE' not in self.request.headers:
            raise AttributeError('TUS needs a TUS version')

        if 'X-UPLOAD-FILENAME' in self.request.headers:
            filename = self.request.headers['X-UPLOAD-FILENAME']
        elif 'UPLOAD-FILENAME' in self.request.headers:
            filename = self.request.headers['UPLOAD-FILENAME']
        elif 'UPLOAD-METADATA' not in self.request.headers:
            filename = uuid.uuid4().hex
        else:
            filename = self.request.headers['UPLOAD-METADATA']
            filename = base64.b64decode(filename.split()[1]).decode('utf-8')
        if extension is None and '.' in filename:
            extension = filename.split('.')[-1]

        resumable_uri_date = datetime.now(tz=tzutc())
        await self.dm.update(
            content_type=self.request.content_type,
            md5=md5,
            filename=filename,
            extension=extension,
            size=size,
            resumable_uri_date=resumable_uri_date,
            current_upload=current_upload)

        await self.file_storage_manager.start(self.dm)

        # Location will need to be adapted on aiohttp 1.1.x
        resp = Response(headers={
            'Location': IAbsoluteURL(
                self.context, self.request)() + '/@tusupload/' + self.field.__name__,  # noqa
            'Tus-Resumable': '1.0.0',
            'Access-Control-Expose-Headers': 'Location,Tus-Resumable'
        }, status=201)
        return resp

    async def upload(self):
        await self.dm.load()
        md5 = extension = size = None
        if 'X-UPLOAD-MD5HASH' in self.request.headers:
            md5 = self.request.headers['X-UPLOAD-MD5HASH']

        if 'X-UPLOAD-EXTENSION' in self.request.headers:
            extension = self.request.headers['X-UPLOAD-EXTENSION']

        if 'X-UPLOAD-SIZE' in self.request.headers:
            size = int(self.request.headers['X-UPLOAD-SIZE'])
        else:
            if 'Content-Length' in self.request.headers:
                size = int(self.request.headers['Content-Length'])
            else:
                raise AttributeError('x-upload-size or content-length header needed')

        if 'X-UPLOAD-FILENAME' in self.request.headers:
            filename = self.request.headers['X-UPLOAD-FILENAME']
        elif 'X-UPLOAD-FILENAME-B64' in self.request.headers:
            filename = base64.b64decode(
                self.request.headers['X-UPLOAD-FILENAME-B64']).decode("utf-8")
        else:
            filename = uuid.uuid4().hex

        await self.dm.update(
            content_type=self.request.content_type,
            md5=md5,
            filename=filename,
            extension=extension,
            size=size)

        await self.file_storage_manager.start(self.dm)
        self.request._last_read_pos = 0
        data = await read_request_data(self.request, CHUNK_SIZE)

        while data:
            await self.file_storage_manager.append(self.dm, data)
            data = await read_request_data(self.request, CHUNK_SIZE)

        await self.file_storage_manager.finish(self.dm)
        await self.dm.finish()

    async def iter_data(self, *args, **kwargs):
        async for chunk in self.file_storage_manager.iter_data(self.dm):
            yield chunk

    async def save_file(self, generator, content_type=None, filename=None,
                        extension=None):
        await self.dm.load()
        await self.dm.update(
            content_type=content_type,
            filename=filename or uuid.uuid4().hex,
            extension=extension
        )
        await self.file_storage_manager.start(self.dm)
        size = 0
        async for data in generator():
            size += len(data)
            await self.file_storage_manager.append(self.dm, data)
        await self.dm.update(
            size=size
        )
        await self.file_storage_manager.finish(self.dm)
        await self.dm.finish()

    async def copy(self, from_manager):
        await self.dm.load()
        await from_manager.dm.load()
        await from_manager.file_storage_manager.start(from_manager.dm)
        await self.file_storage_manager.copy(
            self.dm, from_manager.file_storage_manager, from_manager.dm)
        await from_manager.dm.finish()
