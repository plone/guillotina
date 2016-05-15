# -*- coding: utf-8 -*-
from aiohttp import web

from plone.server.utils import locked, tm
from plone.server.view import View


class ContainerView(View):
    async def __call__(self):
        counter = self.resource['__visited__']

        # Lock, update, commit
        async with tm(self.request), locked(counter):
            counter.change(1)

        # getPhysicalPath
        parts = [str(counter()), self.resource['__name__']]
        parent = self.resource.__parent__
        while parent is not None and parent.get('__name__') is not None:
            parts.append(parent['__name__'])
            parent = parent.__parent__
        parts.reverse()

        return web.Response(text='/'.join(parts))
