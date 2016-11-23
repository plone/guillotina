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
        'id': 'admin',
        'password': ''
    },
    'auth_policies': [
        'plone.server.auth.policies.BearerAuthPolicy',
        'plone.server.auth.policies.WSTokenAuthPolicy',
    ],
    'auth_user_identifiers': [
        'plone.server.auth.users.RootUserIdentifier'
    ],
    'auth_token_checker': [
        'plone.server.auth.checkers.SaltedHashPasswordChecker',
    ],
    'default_layers': [],
    'http_methods': {},
    'renderers': collections.OrderedDict(),
    'languages': {},
    'default_permission': '',
    'available_addons': {},
    'api_definition': {},
    'cors': {}
}

SCHEMA_CACHE = {}
PERMISSIONS_CACHE = {}
FACTORY_CACHE = {}
