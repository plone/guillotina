from aiohttp.web import Response as aioResponse
from datetime import datetime
from guillotina import configure
from guillotina.browser import Response
from guillotina.component import query_adapter
from guillotina.interfaces import IFrameFormatsJson
from guillotina.interfaces import IRendered
from guillotina.interfaces import IRendererFormatHtml
from guillotina.interfaces import IRendererFormatJson
from guillotina.interfaces import IRendererFormatPlain
from guillotina.interfaces import IRendererFormatRaw
from guillotina.interfaces import IRenderFormats
from guillotina.interfaces import IRequest
from guillotina.interfaces import IView
from guillotina.interfaces.security import PermissionSetting
from guillotina.profile import profilable
from guillotina.utils import apply_coroutine
from zope.interface.interface import InterfaceClass

import json
import ujson


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


@configure.adapter(for_=IRequest, provides=IRendererFormatPlain)
class RendererFormatPlain(object):
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
    @profilable
    async def __call__(self, value):
        headers = {}
        if _is_guillotina_response(value):
            json_value = value.response
            headers = value.headers
            status = value.status
        else:
            # Not a Response object, don't convert
            return value
        if isinstance(json_value, aioResponse):
            # not actually json
            return json_value

        # Framing of options
        frame = self.request.get('frame')
        frame = self.request.query['frame'] if 'frame' in self.request.query else ''
        if frame:
            framer = query_adapter(self.request, IFrameFormatsJson, frame)
            json_value = await apply_coroutine(framer, json_value)
        resp = aioResponse(text=json.dumps(json_value, cls=GuillotinaJSONEncoder))
        resp.headers.update(headers)
        resp.headers.update(
            {'Content-Type': 'application/json'})
        resp.set_status(status)
        return resp


class StringRenderer(Renderer):
    content_type = 'text/plain'

    def get_body(self, value: Response) -> bytes:
        body = value.response
        if not isinstance(body, bytes):
            if not isinstance(body, str):
                body = ujson.dumps(value.response)
            body = body.encode('utf8')
        return body

    @profilable
    async def __call__(self, value):
        if _is_guillotina_response(value):
            value = aioResponse(
                body=self.get_body(value), status=value.status,
                headers=value.headers)
        if 'content-type' not in value.headers:
            value.headers.update({
                'content-type': self.content_type
            })
        return value


@configure.adapter(
    for_=(IRendererFormatHtml, IView, IRequest),
    provides=IRendered)
class RendererHtml(StringRenderer):
    content_type = 'text/html'

    def get_body(self, value: Response) -> bytes:
        body = super().get_body(value)
        if b'<html' not in body:
            body = b'<html><body>' + body + b'</body></html>'
        return body


@configure.adapter(
    for_=(IRendererFormatPlain, IView, IRequest),
    provides=IRendered)
class RendererPlain(StringRenderer):
    content_type = 'text/plain'


@configure.adapter(
    for_=(IRendererFormatRaw, IView, IRequest),
    provides=IRendered)
class RendererRaw(Renderer):

    @profilable
    def guess_response(self, value):
        resp = value.response
        if type(resp) in (dict, list, int, float, bool):
            resp = aioResponse(body=bytes(json.dumps(resp, cls=GuillotinaJSONEncoder), 'utf-8'))
            resp.headers['Content-Type'] = 'application/json'
        elif isinstance(resp, str):
            original_resp = resp
            resp = aioResponse(body=bytes(resp, 'utf-8'))
            if '<html' in original_resp:
                resp.headers['Content-Type'] = 'text/html'
            else:
                resp.headers['Content-Type'] = 'text/plain'
        elif resp is None:
            # missing result...
            resp = aioResponse(body=b'{}')
            resp.headers['Content-Type'] = 'application/json'

        resp.headers.update(value.headers)
        if not resp.prepared:
            resp.set_status(value.status)
        return resp

    @profilable
    async def __call__(self, value):
        resp = value
        if isinstance(value, Response):
            resp = self.guess_response(value)
        return resp
