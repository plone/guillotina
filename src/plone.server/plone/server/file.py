# -*- encoding: utf-8 -*-
from persistent import Persistent
from plone.server.interfaces import IFile
from plone.server.interfaces import IFileField
from plone.server.interfaces import IFileManager
from plone.server.interfaces import IRequest
from plone.server.interfaces import IResource
from plone.server.interfaces import IStorage
from plone.server.interfaces import NotStorable
from ZODB.blob import Blob
from zope.component import adapter
from zope.component import getUtility
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

    file_type = getattr(file, 'contentType', None)
    if file_type:
        return file_type

    filename = getattr(file, 'filename', filename)
    if filename:
        extension = os.path.splitext(filename)[1].lower()
        return mimetypes.types_map.get(extension, 'application/octet-stream')

    return default


@adapter(IResource, IRequest, IFileField)
@implementer(IFileManager)
class BasicFileManager(object):

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

    async def upload(self):
        chunk_size = 8400
        file = self.field.get(self.field.context)
        if file is None:
            file = BasicFile()
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
        resp.content_type = file.contentType
        resp.content_length = file.size
        await resp.prepare(self.request)
        resp.write(file.data)
        await resp.drain()
        return resp


@implementer(IFile)
class BasicFile(Persistent):

    filename = FieldProperty(IFile['filename'])

    def __init__(self, data='', contentType='', filename=None):
        if (
            filename is not None and
            contentType in ('', 'application/octet-stream')
        ):
            contentType = get_contenttype(filename=filename)
        self.contentType = contentType
        self._blob = Blob()
        f = self._blob.open('w')
        f.write(b'')
        f.close()
        self._setData(data)
        self.filename = filename

    def open(self, mode='r'):
        if mode != 'r' and 'size' in self.__dict__:
            del self.__dict__['size']
        return self._blob.open(mode)

    def openDetached(self):
        return open(self._blob.committed(), 'rb')

    def _setData(self, data):
        if 'size' in self.__dict__:
            del self.__dict__['size']
        # Search for a storable that is able to store the data
        dottedName = '.'.join((data.__class__.__module__,
                               data.__class__.__name__))
        storable = getUtility(IStorage, name=dottedName)
        storable.store(data, self._blob)

    def _getData(self):
        fp = self._blob.open('r')
        data = fp.read()
        fp.close()
        return data

    _data = property(_getData, _setData)
    data = property(_getData, _setData)

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

    def getSize(self):
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


# This file was borrowed from z3c.blobfile and is licensed under the terms of
# the ZPL.


MAXCHUNKSIZE = 1 << 16


@implementer(IStorage)
class StringStorable(object):

    def store(self, data, blob):
        if not isinstance(data, str):
            raise NotStorable('Could not store data (not of "str" type).')

        with blob.open('w') as fp:
            fp.write(bytes(data, encoding='utf-8'))


@implementer(IStorage)
class BytesStorable(StringStorable):

    def store(self, data, blob):
        if not isinstance(data, str):
            raise NotStorable('Could not store data (not of "unicode" type).')

        StringStorable.store(self, data, blob)


@implementer(IStorage)
class FileDescriptorStorable(object):

    def store(self, data, blob):
        if not isinstance(data, io.IOBase):
            raise NotStorable('Could not store data (not of "file").')

        filename = getattr(data, 'name', None)
        if filename is not None:
            blob.consumeFile(filename)
            return
