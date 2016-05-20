# -*- coding: utf-8 -*-
from calendar import timegm
from collections import OrderedDict
from datetime import datetime
from plone.registry import field
from plone.registry.interfaces import IRegistry
from plone.server.async import IAsyncUtility
from plone.server.auth.participation import AnonymousUser
from plone.server.auth.participation import PloneUser
from zope.interface import Interface
from zope.component import getUtility

import aiohttp
import asyncio
import jwt
import logging


logger = logging.getLogger(__name__)

# Asyncio Utility


class IOAuth(IAsyncUtility):
    pass


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


class OAuth(object):
    async def initialize(
            self,
            app=None,
            server=None,
            jwt_secret=None,
            jwt_algorithm=None,
            client_id=None,
            client_password=None):
        self.app = app
        self._server = server
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._client_id = client_id
        self._client_password = client_password
        self._auth_code = None
        self._service_token = None
        # self.service_token = call_auth()
        while(True):
            await asyncio.sleep(1)
            print('test')  # noqa

    @property
    def auth_code(self):
        if self._auth_code:
            if self._auth_code['exp'] > timegm(datetime.utcnow().utctimetuple()):
                return self._auth_code['auth_code']
        result = self.call_auth('getAuthCode', {
            'client_id': self._client_id,
            'scope': self.scope,
            'response_type': 'code'
        })

        if result:
            self._auth_code = jwt.decode(
                result.text,
                self.jwt_secret,
                algorithms=[self._jwt_algorithm])
            return self._auth_code['auth_code']
        return None

    async def call_auth(self, call, params, **kw):
        method, url = REST_API[call]
        with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(self._server + url, params=params) as resp:
                    if resp.status == 200:
                        return jwt.decode(
                            resp.text(),
                            self._jwt_secret,
                            algorithms=[self._jwt_algorithm])
            elif method == 'POST':
                async with session.post(self._server + url, data=params) as resp:
                    if resp.status == 200:
                        return jwt.decode(
                            resp.text(),
                            self._jwt_secret,
                            algorithms=[self._jwt_algorithm])

oauth = OAuth()


class PloneJWTExtraction(object):
    """User jwt token extraction."""

    def __init__(self, request):
        self.request = request
        self.config = getUtility(IOAuth)
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
                    self.config._jwt_secret,
                    algorithms=[self.config._jwt_algorithm])
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
        self.token = self.request._cache_credentials['jwt']
        self.id = 'User'
        self._properties = OrderedDict()

        oauth_utility = getUtility(IOAuth)

        result = oauth_utility.call_auth(self._init_call, {
            # 'service_token': plugin.service_token,
            'user_token': self.token['token'],
            'scope': request.site.id,
            'user': id
        })
        if not result:
            raise KeyError('Not a plone.oauth User')

        self._init_data(result)

    def _init_data(self, user_data):
        self._roles = user_data['result']['roles']
        self._groups = user_data['result']['groups']
        self.name = user_data['result']['name']

        if len(self._roles) == 0:
            logger.error('User without roles in this scope')
            raise KeyError('Plone OAuth User has no roles in this Scope')
