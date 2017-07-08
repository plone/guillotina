# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.auth import authenticate_request
from guillotina.auth.users import AnonymousUser
from guillotina.interfaces import Allow
from guillotina.interfaces import IParticipation
from guillotina.interfaces import IRequest


class AnonymousParticipation(object):

    def __init__(self, request):
        self.principal = AnonymousUser(request)
        self.principal._roles['guillotina.Anonymous'] = Allow
        self.interaction = None


@configure.adapter(for_=IRequest, provides=IParticipation)
class GuillotinaParticipation(object):
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
                if hasattr(user, 'roles') and 'guillotina.Authenticated' not in user.roles:
                    user.roles['guillotina.Authenticated'] = 1
        else:
            self.principal = getattr(self.request, '_cache_user', None)
        self.interaction = None
