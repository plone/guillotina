# -*- coding: utf-8 -*-
from plone.server.auth import authenticate_request
from plone.server.interfaces import IRequest
from plone.server.transactions import get_current_request
from zope.component import adapter
from zope.interface import implementer
from zope.security.interfaces import IParticipation


ROOT_USER_ID = 'RootUser'


class RootUser(object):
    def __init__(self, password):
        self.id = ROOT_USER_ID
        self.password = password
        self.groups = ['Managers']
        self._roles = {}
        self._properties = {}


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
            # Special Case its a Root Manager user
            self._roles['plone.SiteAdmin'] = 1
            self._roles['plone.SiteDeleter'] = 1
            self._roles['plone.Owner'] = 1


@adapter(IRequest)
@implementer(IParticipation)
class PloneParticipation(object):
    principal = None

    def __init__(self, request):
        self.request = request

    async def __call__(self):
        # Cached user
        if not hasattr(self.request, '_cache_user'):
            user = await authenticate_request(self.request)
            if user:
                self.request._cache_user = user
                self.principal = user
        else:
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
