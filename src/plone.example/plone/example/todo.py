# -*- encoding: utf-8 -*-
from aiohttp.web import Response
from plone.supermodel import model
from zope import schema


class ITodo(model.Schema):
    title = schema.TextLine(title=u"Title",
                            required=False)
    done = schema.Bool(title=u"Done",
                       required=False)


class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        return Response(text='Hello World!')
