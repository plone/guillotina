# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import Service
from plone.server.api.service import DownloadService
from plone.server.browser import get_physical_path
from zope.component import getMultiAdapter
import mimetypes
from aiohttp.web import StreamResponse
from os.path import basename
import aiohttp


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
