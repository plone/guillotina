# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from plone.server.interfaces import IRequest
from plone.server.registry import ACTIVE_AUTH_EXTRACTION_KEY
from plone.server.registry import ACTIVE_AUTH_USER_KEY
from plone.server.utils import import_class
from zope.component import adapter
from zope.interface import implementer
from zope.security.interfaces import IParticipation


class PloneUser(object):

    def __init__(self, request):
        self.id = 'plone'
        self.request = request
        self._groups = []
        self._roles = []
        self._properties = {}

    @property
    def groups(self):
        return self._groups


class AnonymousUser(PloneUser):

    def __init__(self, request):
        self.id = 'Anonymous User'
        self.request = request
        self.groups = ()


@adapter(IRequest)
@implementer(IParticipation)
class PloneParticipation(object):

    def __init__(self, request):
        self.request = request

    async def __call__(self):
        # Cached user
        if not hasattr(self.request, '__cache_user'):
            # Get settings or
            settings = self.request.site_components.queryUtility(IRegistry) or {}

            # Plugin to extract the credentials to request._cache_credentials
            plugins = settings.get(ACTIVE_AUTH_EXTRACTION_KEY, [])
            for plugin in plugins:
                plugin_object = import_class(plugin)
                await plugin_object(self.request).extract_user()

            # Plugin to set the user to request._cache_user
            plugins = settings.get(ACTIVE_AUTH_USER_KEY, [])
            for plugin in plugins:
                plugin_object = import_class(plugin)
                await plugin_object(self.request).create_user()

        self.principal = getattr(self.request, '_cache_user', None)
        self.interaction = None


class ZopeAuthentication(object):

    def getPrincipal(self, ident):
        return PloneUser(None)
