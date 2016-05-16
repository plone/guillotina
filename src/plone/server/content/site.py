# -*- coding: utf-8 -*-
from aiohttp.web import Response
from plone.registry.interfaces import IRegistry
from plone.server.content import Container
from plone.server.interfaces import IRequest
from plone.server.interfaces import IView
from zope.component import adapter
from zope.component.interfaces import ISite
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer


# noinspection PyPep8Naming
@implementer(ISite)
class Site(Container):

    def __init__(self):
        super(Site, self).__init__()
        self['_components'] = PersistentComponents()

    def getSiteManager(self):
        return self['_components']

    def setSiteManager(self, sitemanager):
        self['_components'] = sitemanager


@adapter(ISite, IRequest)
@implementer(IView)
class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        registry = self.request.registry.getUtility(IRegistry)
        return Response(text=str(registry))
