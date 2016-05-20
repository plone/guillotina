# -*- coding: utf-8 -*-
from collections import OrderedDict
from plone.registry import field
from plone.registry.interfaces import IRegistry
from plone.server.async import IAsyncUtility
from plone.server.auth.participation import AnonymousUser
from plone.server.auth.participation import PloneUser
from zope.interface import Interface

import aiohttp
import asyncio
import jwt
import logging


logger = logging.getLogger(__name__)

# Asyncio Utility


class IOAuth(IAsyncUtility):
    pass


class OAuth(object):
    async def initialize(self, app=None, request=None):
        self.app = app
        self.request = request
        while(True):
            await asyncio.sleep(1)
            print('test')  # noqa


oauth = OAuth()


class IPloneJWTExtractionConfig(Interface):

    secret = field.TextLine(
        title=u'JWTSecret',
        default='secret',
    )

    algorithm = field.TextLine(
        title=u'Algorithm',
        default='HS256',
    )


class IPloneOAuthConfig(Interface):

    server = field.TextLine(
        title=u'Server',
        default='http://localhost:6542',
    )

    secret = field.TextLine(
        title=u'JWTSecret',
        default='secret',
    )

    algorithm = field.TextLine(
        title=u'Algorithm',
        default='HS256',
    )

    client_id = field.TextLine(
        title=u'ClientID',
        default='11',
    )

    client_password = field.TextLine(
        title=u'ClientPassword',
        default='2020Plone',
    )


REST_API = {
    'getAuthCode': ['GET', 'get_authorization_code'],
    'getAuthToken': ['POST', 'get_auth_token'],
    'searchUser': ['POST', 'search_user'],
    'validToken': ['POST', 'valid_token'],
    'getUser': ['POST', 'get_user'],
    'getGroup': ['POST', 'get_group'],
    'getScopeUsers': ['GET', 'get_users'],
    'getScopes': ['GET', 'get_scopes'],
    'grantGlobalRoles': ['POST', 'grant_scope_roles'],
    'revokeGlobalRoles': ['POST', 'deny_scope_roles'],
}


async def call_auth(base_uri, call, params, **kw):
    method, url = REST_API[call]
    with aiohttp.ClientSession() as session:
        if method == 'GET':
            async with session.get(base_uri + url, params=params) as resp:
                if resp.status == 200:
                    return resp.text()
        elif method == 'POST':
            async with session.post(base_uri + url, data=params) as resp:
                if resp.status == 200:
                    return resp.text()


class PloneJWTExtraction(object):
    """User jwt token extraction."""

    def __init__(self, request):
        self.request = request
        settings = request.site_components.getUtility(IRegistry)
        self.config = settings.forInterface(
            IPloneJWTExtractionConfig)
        self.request._cache_credentials = self.extract_user()

    def extract_user(self):
        header_auth = self.request.headers.get('AUTHORIZATION')
        creds = {}
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'bearer':
                token = encoded_token.encode('ascii')
                creds['jwt'] = jwt.decode(
                    token,
                    self.config.secret,
                    algorithms=[self.config.algorithm])
        return creds


class OAuthPloneUserFactory(object):

    def __init__(self, request):
        self.request = request
        if 'token' in self.request._cache_credentials:
            user = AnonymousUser(request)
        else:
            try:
                user = OAuthPloneUser(request)
            except KeyError:
                user = AnonymousUser(request)
        self.request._cache_user = user


class OAuthPloneUser(PloneUser):

    _init_call = 'getUser'
    _search_param = 'user'

    def __init__(self, request):
        super(OAuthPloneUser, self).__init__(request)
        settings = request.site_components.getUtility(IRegistry)
        self.token = self.request._cache_credentials['jwt']
        self.config = settings.forInterface(
            IPloneOAuthConfig)
        self.id = 'User'
        self._properties = OrderedDict()

        result = call_auth(self.config.server, self._init_call, {
            # 'service_token': plugin.service_token,
            'user_token': self.token['token'],
            'scope': request.site.id,
            'user': id
        })
        if not result:
            raise KeyError('Not a plone.oauth User')
        user_data = jwt.decode(
            result.text,
            self.config.secret,
            algorithms=[self.config.algorithm])

        self._init_data(user_data)

    def _init_data(self, user_data):
        self._roles = user_data['result']['roles']
        self._groups = user_data['result']['groups']
        self.name = user_data['result']['name']

        if len(self._roles) == 0:
            logger.error('User without roles in this scope')
            raise KeyError('Plone OAuth User has no roles in this Scope')
