# -*- coding: utf-8 -*-
from calendar import timegm
from collections import OrderedDict
from datetime import datetime
from plone.registry import field
from plone.registry.interfaces import IRegistry
from plone.server.async import IAsyncUtility
from plone.server.auth.participation import AnonymousUser
from plone.server.auth.participation import PloneUser
from zope.component import getUtility
from zope.interface import Interface

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

    def __init__(self, settings):
        self.settings = settings
        self._server = settings['server']
        self._jwt_secret = settings['jwt_secret']
        self._jwt_algorithm = settings['jwt_algorithm']
        self._client_id = settings['client_id']
        self._client_password = settings['client_password']

    async def initialize(self, app=None):
        self.app = app
        self._auth_code = None
        self._service_token = None
        # self.service_token = call_auth()
        while(True):
            logger.debug'Renew token')
            now = timegm(datetime.utcnow().utctimetuple())
            await self.get_service_token()
            expiration = self._service_token['exp']
            time_to_sleep = expiration - now
            await asyncio.sleep(time_to_sleep)

    @property
    async def auth_code(self):
        if self._auth_code:
            now = timegm(datetime.utcnow().utctimetuple())
            if self._auth_code['exp'] > now:
                return self._auth_code['auth_code']
        result = await self.call_auth('getAuthCode', {
            'client_id': self._client_id,
            'scope': 'plone',
            'response_type': 'code'
        })

        if result:
            self._auth_code = jwt.decode(
                result.text,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm])
            return self._auth_code['auth_code']
        return None

    async def get_service_token(self):
        if self._service_token:
            now = timegm(datetime.utcnow().utctimetuple())
            if self._service_token['exp'] > now:
                return self._service_token['access_token']
        logger.info('SERVICE')
        result = await self.call_auth('getAuthToken', {
            'code': await self.auth_code,
            'client_id': self._client_id,
            'client_secret': self._client_password,
            'grant_type': 'authorization_code',
            'scope': 'plone'
        })
        if result:
            self._service_token = jwt.decode(
                result.text,
                self.jwt_secret,
                algorithms=[self._jwt_algorithm])
        else:
            self._service_token = None

    def validate_token(self, request, token):
        scope = request.site.id

        loop = asyncio.get_event_loop()
        future = asyncio.Future()
        asyncio.ensure_future(self.call_auth(
            'validToken',
            params={
                'code': self._service_token,
                'token': token,
                'scope': scope
            },
            future=future
        ))
        loop.run_until_complete(future)
        result = future.result()
        if result:
            plain_result = jwt.decode(
                result.text,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm])
            if 'user' in plain_result:
                return plain_result['user']
            else:
                None
        return None

    async def call_auth(self, call, params, future=None, **kw):
        method, url = REST_API[call]
        result = None
        with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(
                        self._server + url, params=params) as resp:
                    if resp.status == 200:
                        result = jwt.decode(
                            resp.text(),
                            self._jwt_secret,
                            algorithms=[self._jwt_algorithm])
            elif method == 'POST':
                async with session.post(
                        self._server + url, data=params) as resp:
                    if resp.status == 200:
                        result = jwt.decode(
                            resp.text(),
                            self._jwt_secret,
                            algorithms=[self._jwt_algorithm])
        if future is not None:
            future.set_result(result)
        else:
            return future


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

                oauth_utility = getUtility(IOAuth)
                creds['user'] = oauth_utility.validate_token(
                    self.request,
                    creds['token'])

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

        loop = asyncio.get_event_loop()
        future = asyncio.Future()
        asyncio.ensure_future(oauth_utility.call_auth(
            self._init_call,
            params={self._search_param: id},
            future=future
        ))
        loop.run_until_complete(future)
        result = future.result()

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
