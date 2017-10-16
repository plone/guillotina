# -*- coding: utf-8 -*-
from copy import deepcopy
from guillotina.auth.users import ROOT_USER_ID
from guillotina.browser import View
from guillotina.content import Resource
from guillotina.directives import index
from guillotina.directives import metadata
from guillotina.interfaces import IResource
from guillotina.schema import JSONField
from guillotina.schema import List
from guillotina.utils import lazy_apply
from zope.interface import implementer

import aiohttp
import base64
import guillotina.patch  # noqa
import json
import os


TESTING_PORT = 55001

TESTING_SETTINGS = {
    "databases": [
        {
            "db": {
                "storage": "DUMMY",
                "name": "guillotina"
            }
        },
    ],
    "port": TESTING_PORT,
    "static": {
        "static": os.path.dirname(os.path.realpath(__file__)),
        "module_static": 'guillotina:',
        'favicon.ico': os.path.join(os.path.dirname(os.path.realpath(__file__)), '__init__.py')
    },
    "jsapps": {
        "jsapp_static": os.path.dirname(os.path.realpath(__file__)) + '/tests'
    },
    "default_static_filenames": ['teststatic.txt'],
    "creator": {
        "admin": "admin",
        "password": "admin"
    },
    "cors": {
        "allow_origin": ["*"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660
    },
    "root_user": {
        "password": "admin"
    },
    "jwt": {
        "secret": "foobar",
        "algorithm": "HS256"
    },
    "utilities": []
}

QUEUE_UTILITY_CONFIG = {
    "provides": "guillotina.async.IQueueUtility",
    "factory": "guillotina.async.QueueUtility",
    "settings": {}
}


ADMIN_TOKEN = base64.b64encode(
    '{}:{}'.format(ROOT_USER_ID, TESTING_SETTINGS['root_user']['password']).encode(
        'utf-8')).decode('utf-8')
DEBUG = False

TERM_SCHEMA = json.dumps({
    'type': 'object',
    'properties': {
        'label': {'type': 'string'},
        'number': {'type': 'number'}
    },
})


_configurators = []


def configure_with(func):
    _configurators.append(func)


def get_settings(override_settings={}):
    settings = deepcopy(TESTING_SETTINGS)
    for func in _configurators:
        lazy_apply(func, settings, _configurators)
    return settings


class IExample(IResource):

    metadata('categories')

    index('categories', type='nested')
    categories = List(
        title='categories',
        default=[],
        value_type=JSONField(
            title='term',
            schema=TERM_SCHEMA)
    )


@implementer(IExample)
class Example(Resource):
    pass


class AsyncMockView(View):

    def __init__(self, context, request, func, *args, **kwargs):
        self.context = context
        self.request = request
        self.func = func
        self.args = args
        self.kwargs = kwargs

    async def __call__(self):
        await self.func(*self.args, **self.kwargs)


class GuillotinaRequester(object):

    def __init__(self, uri=None, server=None):
        self.uri = uri
        self.server = server

    async def __call__(
            self,
            method,
            path,
            params=None,
            data=None,
            authenticated=True,
            auth_type='Basic',
            headers={},
            token=ADMIN_TOKEN,
            accept='application/json'):

        settings = {}
        settings['headers'] = headers
        if accept is not None:
            settings['headers']['ACCEPT'] = accept
        if authenticated and token is not None:
            settings['headers']['AUTHORIZATION'] = '{} {}'.format(
                auth_type, token)

        settings['params'] = params
        settings['data'] = data
        async with aiohttp.ClientSession() as session:
            operation = getattr(session, method.lower(), None)
            if operation:
                if self.server is not None:
                    resp = await operation(self.server.make_url(path), **settings)
                else:
                    resp = await operation(self.uri + path, **settings)
                return resp
        return None
