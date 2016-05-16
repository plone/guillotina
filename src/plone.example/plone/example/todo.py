# -*- encoding: utf-8 -*-
from aiohttp.web import Response
from zope.interface import Attribute
from zope.interface import Interface


class ITodo(Interface):
    title = Attribute("""Title""")
    done = Attribute("""Done""")


class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        return Response(text='Hello World!')
