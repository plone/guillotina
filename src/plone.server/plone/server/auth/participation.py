# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from plone.server.interfaces import IRequest
from plone.server.registry import ACTIVE_AUTH_EXTRACTION_KEY
from plone.server.registry import ACTIVE_AUTH_USER_KEY
from plone.server.utils import import_class
from zope.component import adapter
from zope.interface import implementer
from zope.security.interfaces import IParticipation
from plone.server.transactions import get_current_request


class RootParticipation(object):

    def __init__(self, request):
        self.principal = PloneUser(request)
        self.principal.id = 'RootUser'

        self.principal._groups.append('Managers')
        self.interaction = None


class AnonymousParticipation(object):

    def __init__(self, request):
        self.principal = AnonymousUser(request)
        self.principal._roles['plone.Anonymous'] = 1
        self.interaction = None


class PloneUser(object):

    def __init__(self, request):
        self.id = 'plone'
        self.request = request
        self._groups = []
        self._roles = {}
        self._properties = {}

    @property
    def groups(self):
        return self._groups


class AnonymousUser(PloneUser):

    def __init__(self, request):
        super(AnonymousUser, self).__init__(request)
        self.id = 'Anonymous User'


class PloneGroup(PloneUser):
    def __init__(self, request, ident):
        super(PloneGroup, self).__init__(request)
        self.id = ident

        if ident == 'Managers':
            # Special Case its a Manager user
            self._roles['plone.SiteCreator'] = 1
            self._roles['plone.Member'] = 1
            self._roles['plone.Reader'] = 1
            self._roles['plone.Editor'] = 1
            self._roles['plone.Reviewer'] = 1
            self._roles['plone.SiteAdmin'] = 1
            self._roles['plone.ContentManager'] = 1
            self._roles['plone.SiteCreator'] = 1
            self._roles['plone.SiteDeleter'] = 1
            self._roles['plone.Manager'] = 1
        # else:
        #     # Cached group TODO : Needs better implementation
        #     if not hasattr(self.request, '__cache_group'):
        #         settings = request.site_components.queryUtility(IRegistry) or {}
        #         plugins = settings.get(GET_GROUPS_KEY, [])
        #         for plugin in plugins:
        #             plugin_object = import_class(plugin)
        #             plugin_object(request).get_group(ident)
        #     cache_group = getattr(self.request, '__cache_group', None)
        #     if cache_group:
        #         self._roles.update(self._cache_group._roles)
        #         self._properties.update(self._cache_group._properties)
        #         self._groups.update(self._cache_group._groups)


@adapter(IRequest)
@implementer(IParticipation)
class PloneParticipation(object):

    def __init__(self, request):
        self.request = request

    async def __call__(self):
        # Cached user
        if not hasattr(self.request, '_cache_user'):
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
    """ Class used to get groups. """

    def getPrincipal(self, ident):
        request = get_current_request()
        if not hasattr(request, '_cache_groups'):
            request._cache_groups = {}
        if ident not in request._cache_groups.keys():
            request._cache_groups[ident] = PloneGroup(request, ident)
        return request._cache_groups[ident]
