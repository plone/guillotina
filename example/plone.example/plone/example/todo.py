# -*- encoding: utf-8 -*-
from aiohttp.web import Response
from zope.interface import Interface
from zope.interface import Attribute
from plone.registry.interfaces import IRegistry


class ITodo(Interface):
    title = Attribute("""Title""")
    done = Attribute("""Done""")


class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        registry = self.request.registry.getUtility(IRegistry)
        return Response(text=str(registry))