# -*- encoding: utf-8 -*-
from aiohttp.web import json_response
from aiohttp.web import Response as aioResponse
from plone.server.interfaces import IRendered
from plone.server.interfaces import IRenderFormats
from plone.server.interfaces import IFrameFormats
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from plone.server.browser import Response
from zope.component import adapter
from zope.interface import implementer
from zope.component import queryAdapter
import json


# Marker objects/interfaces to look for

class IRendererFormatHtml(IRenderFormats):
    pass


class IRendererFormatJson(IRenderFormats):
    pass

class IRendererFormatRaw(IRenderFormats):
    pass


class IFrameFormatsJson(IFrameFormats):
    pass


@adapter(IRequest)
@implementer(IRenderFormats)
class RendererFormats(object):
    def __init__(self, request):
        self.request = request


@adapter(IRequest)
@implementer(IRendererFormatJson)
class RendererFormatJson(object):
    def __init__(self, request):
        self.request = request


@adapter(IRequest)
@implementer(IRendererFormatHtml)
class RendererFormatHtml(object):
    def __init__(self, request):
        self.request = request

@adapter(IRequest)
@implementer(IRendererFormatRaw)
class RendererFormatRaw(object):
    def __init__(self, request):
        self.request = request

# Real objects


@adapter(IRenderFormats, IView, IRequest)
@implementer(IRendered)
class Renderer(object):

    def __init__(self, renderformat, view, request):
        self.view = view
        self.request = request
        self.renderformat = renderformat


@adapter(IRendererFormatJson, IView, IRequest)
@implementer(IRendered)
class RendererJson(Renderer):
    async def __call__(self, value):
        headers = {}
        if hasattr(value, '__class__') and issubclass(value.__class__, Response):
            json_value = value.response
            headers = value.headers
            status = value.status
        else:
            # Not a Response object, don't convert
            return value
        # Framing of options
        frame = self.request.get('frame')
        frame = self.request.GET['frame'] if 'frame' in self.request.GET else ''
        if frame:
            framer = queryAdapter(self.request, IFrameFormatsJson, frame)
            json_value = framer(json_value)
        resp = json_response(json_value)
        resp.headers.update(headers)
        resp.headers.update(
            {'Content-Type': 'application/json'})
        resp.set_status(status)
        # Actions / workflow / roles

        return resp


@adapter(IRendererFormatHtml, IView, IRequest)
@implementer(IRendered)
class RendererHtml(Renderer):
    async def __call__(self, value):
        # Safe html transformation
        return value


@adapter(IRendererFormatRaw, IView, IRequest)
@implementer(IRendered)
class RendererRaw(Renderer):
    async def __call__(self, value):
        if hasattr(value, '__class__') and issubclass(value.__class__, Response):
            resp = value.response
            if isinstance(resp, dict):
                resp = aioResponse(body=bytes(json.dumps(resp), 'utf-8'))
            resp.headers.update(value.headers)
            resp.set_status(value.status)
        else:
            resp = value
        return resp

