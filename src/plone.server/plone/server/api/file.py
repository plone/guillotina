# -*- coding: utf-8 -*-
from aiohttp.web import StreamResponse
from os.path import basename
from plone.server.api.service import DownloadService
from plone.server.api.service import Service
from plone.server.api.service import TraversableDownloadService
from plone.server.api.service import TraversableFieldService
from plone.server.interfaces import IFileManager
from zope.component import getMultiAdapter

import aiohttp
import mimetypes


# Static File
class DefaultGET(DownloadService):

    async def __call__(self):
        if hasattr(self.context, '_file_path'):
            with open(self.context._file_path, 'rb') as f:
                filename = basename(self.context._file_path)
                resp = StreamResponse(headers=aiohttp.MultiDict({
                    'CONTENT-DISPOSITION': 'attachment; filename="%s"' % filename
                }))
                resp.content_type = mimetypes.guess_type(self.context._file_path)
                data = f.read()
                resp.content_length = len(data)
                await resp.prepare(self.request)

                resp.write(data)
                return resp


class DefaultPOST(Service):
    pass


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    pass


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):
    pass


# Field File

class UploadFile(TraversableFieldService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        import pdb; pdb.set_trace()
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.upload()


class DownloadFile(TraversableDownloadService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.download()


class TusCreateFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_create()


class TusHeadFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_head()


class TusPatchFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_patch()


class TusOptionsFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_options()
