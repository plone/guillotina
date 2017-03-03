# -*- encoding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileField
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IStorage
from guillotina.interfaces import NotStorable
from guillotina.utils import import_class
from persistent import Persistent
from ZODB.blob import Blob
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.schema import Object
from zope.schema.fieldproperty import FieldProperty

import aiohttp
import io
import mimetypes
import os


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


@configure.adapter(
    for_=(IResource, IRequest, IFileField),
    provides=IFileManager)
class BasicFileManager(object):

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

    async def upload(self):
        chunk_size = 8400
        file = self.field.get(self.field.context)
        if file is None:
            filename = None
            if 'X-UPLOAD-FILENAME' in self.request.headers:
                filename = self.request.headers['X-UPLOAD-FILENAME']
            file = BasicFile(filename=filename)
            self.field.set(self.field.context, file)
        with file.open('w') as fd:
            while True:
                chunk = await self.request.content.read(chunk_size)
                if not chunk:
                    break
                fd.write(chunk)

    async def download(self):
        file = self.field.get(self.field.context)
        if file is None:
            raise AttributeError('No field value')

        resp = aiohttp.web.StreamResponse(headers=aiohttp.MultiDict({
            'CONTENT-DISPOSITION': 'attachment; filename="%s"' % file.filename
        }))
        resp.content_type = file.content_type
        resp.content_length = file.size
        await resp.prepare(self.request)
        resp.write(file.data)
        await resp.drain()
        return resp


@implementer(IFile)
class BasicFile(Persistent):

    filename = FieldProperty(IFile['filename'])

    def __init__(self, data='', content_type='', filename=None):
        if (
            filename is not None and
            content_type in ('', 'application/octet-stream')
        ):
            content_type = get_contenttype(filename=filename)
        self.content_type = content_type
        self._blob = Blob()
        f = self._blob.open('w')
        f.write(b'')
        f.close()
        self._set_data(data)
        self.filename = filename

    def open(self, mode='r'):
        if mode != 'r' and 'size' in self.__dict__:
            del self.__dict__['size']
        return self._blob.open(mode)

    def open_detached(self):
        return open(self._blob.committed(), 'rb')

    def _set_data(self, data):
        if 'size' in self.__dict__:
            del self.__dict__['size']
        # Search for a storable that is able to store the data
        dottedName = '.'.join((data.__class__.__module__,
                               data.__class__.__name__))
        storable = getUtility(IStorage, name=dottedName)
        storable.store(data, self._blob)

    def _get_data(self):
        fp = self._blob.open('r')
        data = fp.read()
        fp.close()
        return data

    _data = property(_get_data, _set_data)
    data = property(_get_data, _set_data)

    @property
    def size(self):
        if 'size' in self.__dict__:
            return self.__dict__['size']
        reader = self._blob.open()
        reader.seek(0, 2)
        size = int(reader.tell())
        reader.close()
        self.__dict__['size'] = size
        return size

    def get_size(self):
        return self.size


@implementer(IFileField)
class BasicFileField(Object):
    """A NamedBlobFile field
    """

    _type = BasicFile
    schema = IFile

    def __init__(self, **kw):
        if 'schema' in kw:
            self.schema = kw.pop('schema')
        super(BasicFileField, self).__init__(schema=self.schema, **kw)


@implementer(ICloudFileField)
class CloudFileField(Object):
    """A cloud file hosted file.

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

    async def download(self):
        return await self.real_file_manager.download()

    async def tus_options(self):
        return await self.real_file_manager.tus_options()

    async def tus_head(self):
        return await self.real_file_manager.tus_head()

    async def tus_patch(self):
        return await self.real_file_manager.tus_patch()

    async def tus_create(self):
        return await self.real_file_manager.tus_create()

    async def upload(self):
        return await self.real_file_manager.upload()


# This file was borrowed from z3c.blobfile and is licensed under the terms of
# the ZPL.


MAXCHUNKSIZE = 1 << 16


@implementer(IStorage)
@configure.utility(provides=IStorage, name="builtins.str")
class StringStorable(object):

    def store(self, data, blob):
        if not isinstance(data, str):
            raise NotStorable('Could not store data (not of "str" type).')

        with blob.open('w') as fp:
            fp.write(bytes(data, encoding='utf-8'))


@implementer(IStorage)
@configure.utility(provides=IStorage, name="builtin.bytes")
class BytesStorable(StringStorable):

    def store(self, data, blob):
        if not isinstance(data, str):
            raise NotStorable('Could not store data (not of "unicode" type).')

        StringStorable.store(self, data, blob)


@implementer(IStorage)
@configure.utility(provides=IStorage, name="builtin.file")
class FileDescriptorStorable(object):

    def store(self, data, blob):
        if not isinstance(data, io.IOBase):
            raise NotStorable('Could not store data (not of "file").')

        filename = getattr(data, 'name', None)
        if filename is not None:
            blob.consumeFile(filename)
            return
