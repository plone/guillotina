# -*- coding: utf-8 -*-
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPNotFound
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from zope.component import queryMultiAdapter
from zope.component.interfaces import ISite
from zope.interface import alsoProvides


async def traverse(request, parent, path):
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    context = parent[path[0]]
    context._v_parent = parent

    if ISite.providedBy(context):
        request.registry = context.getSiteManager()

    return await traverse(request, context, path[1:])


class MatchInfo(AbstractMatchInfo):
    def __init__(self, request, resource, view):
        self.request = request
        self.resource = resource
        self.view = view

    def handler(self, request):
        return self.view()

    def get_info(self):
        return {
            'request': self.request,
            'resource': self.resource,
            'view': self.view,
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
        
        view = None
        
        # Site registry lookup
        if hasattr(request, 'registry'):
            view = request.registry.queryMultiAdapter(
                (resource, request), IView)
            
        # Global registry lookup
        if view is None:
            view = queryMultiAdapter(
                (resource, request), IView)
            
        if view is not None:
            return MatchInfo(resource, request, view)
        else:
            print(resource)
            raise HTTPNotFound()

    async def traverse(self, request):
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root_factory()
        if path:
            return await traverse(request, root, path)
        else:
            return root, path
