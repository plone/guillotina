# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import Service
from plone.server.api.service import DownloadService
from plone.server.api.service import TraversableService
from plone.server.api.service import TraversableDownloadService
from plone.server.browser import get_physical_path
from plone.server.interfaces import IFileManager
from zope.component import getMultiAdapter
import mimetypes
from aiohttp.web import StreamResponse
from os.path import basename
import aiohttp
from zope.interface.interfaces import ComponentLookupError
from plone.dexterity.fti import IDexterityFTI
from zope.component import getUtilitiesFor
from zope.component import queryUtility


# Static File
class DefaultGET(DownloadService):

    async def __call__(self):
        if hasattr(self.context, '_file_path'):
            contenttype = mimetypes.guess_type(self.context._file_path)
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

class UploadFile(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the field
            if not hasattr(self.context, traverse[0]):
                raise KeyError('No valid name')

            name = traverse[0]
            schema = queryUtility(IDexterityFTI, name=self.context.portal_type).lookupSchema()

            # Check that its a File Field
            if name not in schema:
                raise KeyError('No valid name')

            self.field = schema[name].bind(self.context)
        else:
            self.field = None
        return self

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks

        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.upload()


class DownloadFile(TraversableDownloadService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = [queryUtility(IDexterityFTI, name=traverse[0])]
        return self

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        if not hasattr(self, 'value'):
            self.value = [x[1] for x in getUtilitiesFor(IDexterityFTI)]
        result = []
        for x in self.value:
            serializer = getMultiAdapter(
                (x, self.request),
                ISerializeToJson)

            result.append(serializer())
        return result
