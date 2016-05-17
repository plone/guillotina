# -*- coding: utf-8 -*-
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPNotFound
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from plone.server.interfaces import ITranslated
from plone.server.interfaces import IRendered
from plone.server.contentnegotiation import content_negotiation
from zope.component import queryMultiAdapter
from zope.component.interfaces import ISite
from zope.interface import alsoProvides
from plone.server import DICT_RENDERS, DICT_METHODS
from plone.registry.interfaces import IRegistry
from plone.server.utils import import_class


async def traverse(request, parent, path):
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    try:
        context = parent[path[0]]
    except TypeError:
        return parent, path

    context._v_parent = parent

    if ISite.providedBy(context):
        request.registry = context.getSiteManager()
        plone_registry = request.registry.getUtility(IRegistry)
        layers = plone_registry.get('plone.server.registry.layers.ILayers.active_layers', [])
        for layer in layers:
            alsoProvides(request, import_class(layer))

    return await traverse(request, context, path[1:])


class MatchInfo(AbstractMatchInfo):
    def __init__(self, request, resource, view, rendered):
        self.request = request
        self.resource = resource
        self.view = view
        self.rendered = rendered

    async def handler(self, request):
        view_result = await self.view()
        return await self.rendered(view_result)

    def get_info(self):
        return {
            'request': self.request,
            'resource': self.resource,
            'view': self.view,
            'rendered': self.rendered
        }

    async def expect_handler(self, request):
        return None

    async def http_exception(self):
        return None


class TraversalRouter(AbstractRouter):
    _root_factory = None

    def __init__(self, root_factory=None):
        self.set_root_factory(root_factory)

    def set_root_factory(self, root_factory):
        self._root_factory = root_factory

    async def resolve(self, request):
        alsoProvides(request, IRequest)
        try:
            resource, tail = await self.traverse(request)
            exc = None
        except Exception as _exc:
            resource = None
            tail = None
            exc = _exc

        request.resource = resource
        request.tail = tail
        request.exc = exc
        if len(tail) == 1:
            view_name = tail[0]
        elif len(tail) == 0:
            view_name = ''
        else:
            raise HTTPNotFound()

        method = DICT_METHODS[request.method]

        renderer, language = content_negotiation(request)
        language_object = language(request)

        resource = queryMultiAdapter(
            (language_object, resource, request), ITranslated).translate()

        # Site registry lookup
        try:
            view = request.registry.queryMultiAdapter(
                (resource, request), method, name=view_name)
        except AttributeError:
            view = None

        # Global registry lookup
        if view is None:
            view = queryMultiAdapter(
                (resource, request), method, name=view_name)

        # We want to check for the content negotiation
        renderer_object = renderer(request)

        rendered = queryMultiAdapter(
            (renderer_object, view, request), IRendered)

        if rendered is not None:
            return MatchInfo(resource, request, view, rendered)
        else:
            raise HTTPNotFound()

    async def traverse(self, request):
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root_factory()
        if path:
            return await traverse(request, root, path)
        else:
            return root, path
