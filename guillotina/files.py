# -*- encoding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IStorage
from guillotina.interfaces import NotStorable
from guillotina.schema import Object
from guillotina.utils import import_class
from zope.interface import alsoProvides
from zope.interface import implementer

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
