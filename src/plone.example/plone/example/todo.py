# -*- encoding: utf-8 -*-
from aiohttp.web import Response
from plone.supermodel import model
from zope import schema
from plone.server.api.service import Service


class ITodo(model.Schema):
    title = schema.TextLine(title=u"Title",
                            required=False)
    done = schema.Bool(title=u"Done",
                       required=False)


class View(Service):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        return Response(text='Hello World!')
