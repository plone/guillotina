# -*- encoding: utf-8 -*-
from aiohttp.helpers import sentinel
from aiohttp.web import Response as aioResponse
from datetime import datetime
from guillotina import configure
from guillotina.browser import Response
from guillotina.component import queryAdapter
from guillotina.interfaces import IFrameFormatsJson
from guillotina.interfaces import IRendered
from guillotina.interfaces import IRendererFormatHtml
from guillotina.interfaces import IRendererFormatJson
from guillotina.interfaces import IRendererFormatRaw
from guillotina.interfaces import IRenderFormats
from guillotina.interfaces import IRequest
from guillotina.interfaces import IView
from guillotina.interfaces.security import PermissionSetting
from guillotina.utils import apply_coroutine
from zope.interface.interface import InterfaceClass

import json


class GuillotinaJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, type):
            return obj.__module__ + '.' + obj.__name__
        elif isinstance(obj, InterfaceClass):
            return [x.__module__ + '.' + x.__name__ for x in obj.__iro__]  # noqa
        try:
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)

        if isinstance(obj, PermissionSetting):
            return obj.get_name()
        if callable(obj):
            return obj.__module__ + '.' + obj.__name__
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


# b/w compat import
PServerJSONEncoder = GuillotinaJSONEncoder


def json_response(data=sentinel, *, text=None, body=None, status=200,
                  reason=None, headers=None, content_type='application/json',
                  dumps=json.dumps):
    if data is not sentinel:
        if text or body:
            raise ValueError(
                "only one of data, text, or body should be specified"
            )
        else:
            text = dumps(data, cls=GuillotinaJSONEncoder)
    return aioResponse(
        text=text, body=body, status=status, reason=reason,
        headers=headers, content_type=content_type)


@configure.adapter(for_=IRequest, provides=IRenderFormats)
class RendererFormats(object):
    def __init__(self, request):
        self.request = request


@configure.adapter(for_=IRequest, provides=IRendererFormatJson)
class RendererFormatJson(object):
    def __init__(self, request):
        self.request = request


@configure.adapter(for_=IRequest, provides=IRendererFormatHtml)
class RendererFormatHtml(object):
    def __init__(self, request):
        self.request = request


@configure.adapter(for_=IRequest, provides=IRendererFormatRaw)
class RendererFormatRaw(object):
    def __init__(self, request):
        self.request = request

# Real objects


@configure.adapter(
    for_=(IRenderFormats, IView, IRequest),
    provides=IRendered)
class Renderer(object):

    def __init__(self, renderformat, view, request):
        self.view = view
        self.request = request
        self.renderformat = renderformat


def _is_guillotina_response(resp):
    return hasattr(resp, '__class__') and issubclass(resp.__class__, Response)


@configure.adapter(
    for_=(IRendererFormatJson, IView, IRequest),
    provides=IRendered)
class RendererJson(Renderer):
    async def __call__(self, value):
        headers = {}
        if _is_guillotina_response(value):
            json_value = value.response
            headers = value.headers
            status = value.status
        else:
            # Not a Response object, don't convert
            return value
        # Framing of options
        frame = self.request.get('frame')
        frame = self.request.query['frame'] if 'frame' in self.request.query else ''
        if frame:
            framer = queryAdapter(self.request, IFrameFormatsJson, frame)
            json_value = await apply_coroutine(framer, json_value)
        resp = json_response(json_value)
        resp.headers.update(headers)
        resp.headers.update(
            {'Content-Type': 'application/json'})
        resp.set_status(status)
        # Actions / workflow / roles

        return resp


@configure.adapter(
    for_=(IRendererFormatHtml, IView, IRequest),
    provides=IRendered)
class RendererHtml(Renderer):
    async def __call__(self, value):
        # Safe html transformation
        if _is_guillotina_response(value):
            body = value.response
            if not isinstance(body, bytes):
                if not isinstance(body, str):
                    body = json.dumps(value.response)
                body = body.encode('utf8')

            value = aioResponse(
                body=body, status=value.status,
                headers=value.headers)
        if 'content-type' not in value.headers:
            value.headers.update({
                'content-type': 'text/html'
            })
        return value


@configure.adapter(
    for_=(IRendererFormatRaw, IView, IRequest),
    provides=IRendered)
class RendererRaw(Renderer):

    def guess_response(self, value):
        resp = value.response
        if type(resp) in (dict, list, int, float, bool):
            resp = aioResponse(body=bytes(json.dumps(resp, cls=GuillotinaJSONEncoder), 'utf-8'))
            resp.headers['Content-Type'] = 'application/json'
        elif isinstance(resp, str):
            resp = aioResponse(body=bytes(resp, 'utf-8'))
            resp.headers['Content-Type'] = 'text/html'
        elif resp is None:
            # missing result...
            resp = aioResponse(body=b'{}')
            resp.headers['Content-Type'] = 'application/json'

        resp.headers.update(value.headers)
        if not resp.prepared:
            resp.set_status(value.status)
        return resp

    async def __call__(self, value):
        resp = value
        if isinstance(value, Response):
            resp = self.guess_response(value)
        return resp
