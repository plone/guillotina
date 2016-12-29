# -*- coding: utf-8 -*-
from aiohttp.web import StreamResponse
from os.path import basename
from plone.server.api.service import DownloadService
from plone.server.api.service import TraversableDownloadService
from plone.server.api.service import TraversableFieldService
from plone.server.interfaces import IFileManager
from zope.component import getMultiAdapter
from plone.server.interfaces import IResource

import aiohttp
import mimetypes
from plone.server.configure import service
from plone.server.interfaces import IStaticFile


# Static File
@service(context=IStaticFile, method='GET', permission='plone.AccessContent')
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


# Field File
@service(context=IResource, method='PATCH', permission='plone.ModifyContent',
         name='@upload')
class UploadFile(TraversableFieldService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.upload()


@service(context=IResource, method='GET', permission='plone.ViewContent',
         name='@download')
class DownloadFile(TraversableDownloadService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.download()


@service(context=IResource, method='POST', permission='plone.ModifyContent',
         name='@tusupload')
class TusCreateFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_create()


@service(context=IResource, method='HEAD', permission='plone.ModifyContent',
         name='@tusupload')
class TusHeadFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_head()


@service(context=IResource, method='PATCH', permission='plone.ModifyContent',
         name='@tusupload')
class TusPatchFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_patch()


@service(context=IResource, method='OPTIONS', permission='plone.AccessPreflight',
         name='@tusupload')
class TusOptionsFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_options()
