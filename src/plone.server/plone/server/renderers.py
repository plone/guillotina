# -*- encoding: utf-8 -*-
from aiohttp.web import json_response
from plone.server.interfaces import (IRendered,
                                     IRenderFormats, IRequest, IView)
from zope.component import adapter
from zope.interface import implementer


# Marker objects/interfaces to look for

class IRendererFormatHtml(IRenderFormats):
    pass


class IRendererFormatJson(IRenderFormats):
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
        return json_response(value)


@adapter(IRendererFormatHtml, IView, IRequest)
@implementer(IRendered)
class RendererHtml(Renderer):
    async def __call__(self):
        return value
