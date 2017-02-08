# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.auth import authenticate_request
from plone.server.auth.users import AnonymousUser
from plone.server.interfaces import IRequest
from zope.security.interfaces import IParticipation
from plone.server.interfaces import Allow


class AnonymousParticipation(object):

    def __init__(self, request):
        self.principal = AnonymousUser(request)
        self.principal._roles['plone.Anonymous'] = Allow
        self.interaction = None


@configure.adapter(for_=IRequest, provides=IParticipation)
class PloneParticipation(object):
    principal = None

    def __init__(self, request):
        self.request = request

    async def __call__(self):
        # Cached user
        if not hasattr(self.request, '_cache_user'):
            user = await authenticate_request(self.request)
            if user is not None:
                self.request._cache_user = user
                self.principal = user
                if hasattr(user, '_roles') and 'plone.Authenticated' not in user._roles:
                    user._roles['plone.Authenticated'] = 1
        else:
            self.principal = getattr(self.request, '_cache_user', None)
        self.interaction = None
