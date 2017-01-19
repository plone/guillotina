# -*- encoding: utf-8 -*-
# create logging
import logging
logger = logging.getLogger('plone.server')

from zope.i18nmessageid import MessageFactory  # noqa
_ = MessageFactory('plone')

# load the patch before anything else.
from plone.server import patch  # noqa
# load defined migrations
from plone.server.migrate import migrations  # noqa

from plone.server import interfaces
from plone.server import languages


import collections


app_settings = {
    "databases": [],
    "address": 8080,
    "static": [],
    "utilities": [],
    "root_user": {
        "password": ""
    },
    "auth_extractors": [
        "plone.server.auth.extractors.BearerAuthPolicy",
        "plone.server.auth.extractors.BasicAuthPolicy",
        "plone.server.auth.extractors.WSTokenAuthPolicy",
    ],
    "auth_user_identifiers": [],
    "auth_token_validators": [
        "plone.server.auth.validators.SaltedHashPasswordValidator",
        "plone.server.auth.validators.JWTValidator"
    ],
    "default_layers": [
        interfaces.IDefaultLayer
    ],
    "http_methods": {
        "PUT": interfaces.IPUT,
        "POST": interfaces.IPOST,
        "PATCH": interfaces.IPATCH,
        "DELETE": interfaces.IDELETE,
        "GET": interfaces.IGET,
        "OPTIONS": interfaces.IOPTIONS,
        "HEAD": interfaces.IHEAD,
        "CONNECT": interfaces.ICONNECT
    },
    "renderers": collections.OrderedDict({
        "application/json": interfaces.IRendererFormatJson,
        "text/html": interfaces.IRendererFormatHtml,
        "*/*": interfaces.IRendererFormatRaw
    }),
    "languages": {
        "en": languages.IEN,
        "en-us": languages.IENUS,
        "ca": languages.ICA
    },
    "default_permission": 'zope.Public',
    "available_addons": {},
    "api_definition": {},
    "cors": {
        "allow_origin": ["http://localhost:8080"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660
    },
    "jwt": {
        "secret": "foobar",
        "algorithm": "HS256"
    }
}

SCHEMA_CACHE = {}
PERMISSIONS_CACHE = {}
FACTORY_CACHE = {}
BEHAVIOR_CACHE = {}
