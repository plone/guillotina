# -*- encoding: utf-8 -*-
from aiohttp.web import json_response
from plone.server.interfaces import IRendered
from plone.server.interfaces import IRenderFormats
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from plone.server.browser import ResponseWithHeaders
from zope.component import adapter
from zope.interface import implementer


# Marker objects/interfaces to look for

class IRendererFormatHtml(IRenderFormats):
    pass


class IRendererFormatJson(IRenderFormats):
    pass


class IRendererFormatRaw(IRenderFormats):
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
        if isinstance(value, ResponseWithHeaders):
            resp = json_response(value.response)
            # Add custom headers
            resp.headers.update(value.headers)
        else:
            if not hasattr(value, 'status_code') or \
                    (hasattr(value, 'status_code') and value.status_code < 400):
                resp = json_response(value)
            else:
                return value
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
        return value

