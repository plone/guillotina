# -*- encoding: utf-8 -*-
from aiohttp.web import Response as aioResponse
from aiohttp.helpers import sentinel
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

# JSON Decoder
from zope.securitypolicy.settings import PermissionSetting


class PServerJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        try:
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)

        if isinstance(obj, PermissionSetting):
            return obj.getName()
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def json_response(data=sentinel, *, text=None, body=None, status=200,
                  reason=None, headers=None, content_type='application/json',
                  dumps=json.dumps):
    if data is not sentinel:
        if text or body:
            raise ValueError(
                "only one of data, text, or body should be specified"
            )
        else:
            text = dumps(data, cls=PServerJSONEncoder)
    return aioResponse(text=text, body=body, status=status, reason=reason,
                    headers=headers, content_type=content_type)

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

