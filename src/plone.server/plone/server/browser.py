# -*- coding: utf-8 -*-
from aiohttp.web import Response
from plone.dexterity.interfaces import IDexterityContent
from plone.registry.interfaces import IRegistry
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from zope.component import adapter
from zope.interface import implementer


@adapter(IDexterityContent, IRequest)
@implementer(IView)
class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.registry = self.request.registry.getUtility(IRegistry)

    async def __call__(self):
        import pdb  # noqa
        pdb.set_trace()  # noqa
        return Response(text=str(self.registry))
