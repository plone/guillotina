# -*- coding: utf-8 -*-
from aiohttp.web import Response
from venusianconfiguration import configure
from plone.server.content import Container
from zope.component.interfaces import ISite
from plone.registry.interfaces import IRegistry
from zope.component.persistentregistry import PersistentComponents
from zope.interface import implementer
from plone.server.interfaces import IView
from plone.server.interfaces import IRequest


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


@configure.adapter.factory(for_=(ISite, IRequest), provides=IView)
class View(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):
        registry = self.request.registry.getUtility(IRegistry)
        return Response(text=str(registry))
