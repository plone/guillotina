# -*- coding: utf-8 -*-
from aiohttp.web import StreamResponse
from guillotina import app_settings
from guillotina import configure
from guillotina.api.content import DefaultOPTIONS
from guillotina.api.service import DownloadService
from guillotina.api.service import TraversableDownloadService
from guillotina.api.service import TraversableFieldService
from guillotina.component import getMultiAdapter
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IResource
from guillotina.interfaces import IStaticDirectory
from guillotina.interfaces import IStaticFile

import mimetypes


# Static File
@configure.service(context=IStaticFile, method='GET', permission='guillotina.AccessContent')
class FileGET(DownloadService):
    async def serve_file(self, fi):
        filepath = str(fi.file_path.absolute())
        filename = fi.file_path.name
        with open(filepath, 'rb') as f:
            resp = StreamResponse()
            resp.content_type, _ = mimetypes.guess_type(filename)

            disposition = 'filename="{}"'.format(filename)
            if 'text' not in resp.content_type:
                disposition = 'attachment; ' + disposition

            resp.headers['CONTENT-DISPOSITION'] = disposition

            data = f.read()
            resp.content_length = len(data)
            await resp.prepare(self.request)

            resp.write(data)
            return resp

    async def __call__(self):
        if hasattr(self.context, 'file_path'):
            return await self.serve_file(self.context)


@configure.service(context=IStaticDirectory, method='GET', permission='guillotina.AccessContent')
class DirectoryGET(FileGET):
    async def __call__(self):
        for possible_default_file in app_settings['default_static_filenames']:
            if possible_default_file in self.context:
                return await self.serve_file(self.context[possible_default_file])


# Field File
@configure.service(context=IResource, method='PATCH', permission='guillotina.ModifyContent',
                   name='@upload')
class UploadFile(TraversableFieldService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.upload()


@configure.service(context=IResource, method='GET', permission='guillotina.ViewContent',
                   name='@download')
class DownloadFile(TraversableDownloadService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.download()


@configure.service(context=IResource, method='POST', permission='guillotina.ModifyContent',
                   name='@tusupload')
class TusCreateFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_create()


@configure.service(context=IResource, method='HEAD', permission='guillotina.ModifyContent',
                   name='@tusupload')
class TusHeadFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_head()


@configure.service(context=IResource, method='PATCH', permission='guillotina.ModifyContent',
                   name='@tusupload')
class TusPatchFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_patch()


@configure.service(context=IResource, method='OPTIONS', permission='guillotina.AccessPreflight',
                   name='@tusupload')
class TusOptionsFile(DefaultOPTIONS, UploadFile):

    async def render(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_options()
