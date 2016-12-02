# -*- encoding: utf-8 -*-
from zope.i18nmessageid import MessageFactory
import collections


_ = MessageFactory('plone')

app_settings = {
    'databases': [],
    'address': 8080,
    'static': [],
    'utilities': [],
    'root_user': {
        'password': ''
    },
    'auth_extractors': [
        'plone.server.auth.extractors.BearerAuthPolicy',
        'plone.server.auth.extractors.BasicAuthPolicy',
        'plone.server.auth.extractors.WSTokenAuthPolicy',
    ],
    'auth_user_identifiers': [],
    'auth_token_validators': [
        'plone.server.auth.validators.SaltedHashPasswordValidator',
        'plone.server.auth.validators.JWTValidator'
    ],
    'default_layers': [],
    'http_methods': {},
    'renderers': collections.OrderedDict(),
    'languages': {},
    'default_permission': '',
    'available_addons': {},
    'api_definition': {},
    'cors': {
        "allow_origin": ['*'],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
        "allow_headers": ['*'],
        "expose_headers": ['*'],
        "allow_credentials": True,
        "max_age": 3660
    },
    'jwt': {
        'secret': 'foobar',
        'algorithm': 'HS256'
    }
}

SCHEMA_CACHE = {}
PERMISSIONS_CACHE = {}
FACTORY_CACHE = {}
BEHAVIOR_CACHE = {}
