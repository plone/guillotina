from .const import CHUNK_SIZE
from .dbfile import DBFile
from aiohttp.web import StreamResponse
from aiohttp.web_exceptions import HTTPNotFound
from datetime import datetime
from datetime import timedelta
from dateutil.tz import tzutc
from guillotina import configure
from guillotina._settings import app_settings
from guillotina.browser import Response
from guillotina.files.utils import read_request_data
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IDBFileField
from guillotina.interfaces import IFileCleanup
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource

import base64
import uuid


@configure.adapter(
    for_=IResource,
    provides=IFileCleanup
)
class DefaultFileCleanup:
    def __init__(self, context):
        pass

    def should_clean(self, **kwargs):
        return True


@configure.adapter(
    for_=(IResource, IRequest, IDBFileField),
    provides=IFileManager)
class DBFileManagerAdapter:

    file_class = DBFile

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

    async def upload(self):
        """In order to support TUS and IO upload.
        """
        try:
            self.field.context.data._p_register()  # register change...
        except AttributeError:
            self.context._p_register()

        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class):
            file = self.file_class(content_type=self.request.content_type)
            self.field.set(self.field.context or self.context, file)
        else:
            self.content_type = self.request.content_type

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
            if 'Content-Length' in self.request.headers:
                file._size = int(self.request.headers['Content-Length'])
            else:
                raise AttributeError('x-upload-size or content-length header needed')

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

        while data:
            await file.append_data(self.context, data)
            data = await read_request_data(self.request, CHUNK_SIZE)

        # Test resp and checksum to finish upload
        await file.finish_upload(self.context)

    async def tus_create(self):
        try:
            self.field.context.data._p_register()  # register change...
        except AttributeError:
            self.context._p_register()

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
            raise AttributeError('TUS needs a TUS version')

        if 'UPLOAD-METADATA' not in self.request.headers:
            file.filename = uuid.uuid4().hex
        else:
            filename = self.request.headers['UPLOAD-METADATA']
            file.filename = base64.b64decode(filename.split()[1]).decode('utf-8')

        file._resumable_uri_date = datetime.now(tz=tzutc())

        await file.init_upload(self.context)
        # Location will need to be adapted on aiohttp 1.1.x
        resp = Response(headers={
            'Location': IAbsoluteURL(self.context, self.request)() + '/@tusupload/' + self.field.__name__,  # noqa
            'Tus-Resumable': '1.0.0',
            'Access-Control-Expose-Headers': 'Location,Tus-Resumable'
        }, status=201)
        return resp

    async def tus_patch(self):
        try:
            self.field.context.data._p_register()  # register change...
        except AttributeError:
            self.context._p_register()

        file = self.field.get(self.field.context or self.context)
        if 'CONTENT-LENGTH' in self.request.headers:
            to_upload = int(self.request.headers['CONTENT-LENGTH'])
        else:
            raise AttributeError('No content-length header')

        try:
            self.field.context.data._p_register()  # register change...
        except AttributeError:
            self.context._p_register()

        if 'UPLOAD-OFFSET' in self.request.headers:
            file._current_upload = int(self.request.headers['UPLOAD-OFFSET'])
        else:
            raise AttributeError('No upload-offset header')

        self.request._last_read_pos = 0
        data = await read_request_data(self.request, to_upload)

        while data:
            await file.append_data(self.context, data)
            data = await read_request_data(self.request, CHUNK_SIZE)

        await file.finish_upload(self.context)
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

        await download_resp.prepare(self.request)
        resp = await file.download(self.context, download_resp)
        return resp

    async def iter_data(self):
        file = self.field.get(self.field.context or self.context)
        if not isinstance(file, self.file_class):
            raise AttributeError('No field value')

        async for chunk in file.iter_data(self.context):
            yield chunk

    async def save_file(self, generator, content_type=None, size=None,
                        filename=None):
        try:
            self.field.context.data._p_register()  # register change...
        except AttributeError:
            self.context._p_register()

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
            await file.append_data(self.context, data)

        await file.finish_upload(self.context)
        return file
