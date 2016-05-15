# -*- coding: utf-8 -*-
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPNotFound
from .traversal import traverse
import logging

log = logging.getLogger(__name__)


class TraversalRouter(AbstractRouter):
    _root_factory = None

    def __init__(self, root_factory=None):
        self.set_root_factory(root_factory)

    def set_root_factory(self, root_factory):
        self._root_factory = root_factory

    async def resolve(self, request):
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

        print(resource)
 
        raise HTTPNotFound()

    async def traverse(self, request):
        path = list(p for p in request.path.split('/') if p)
        root = self._root_factory()
        if path:
            return await traverse(request, root, path)
        else:
            return root, path
