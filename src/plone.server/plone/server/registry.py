# -*- coding: utf-8 -*-
from plone.registry import field
from plone.server import _
from zope.interface import Interface


ACTIVE_AUTH_EXTRACTION_KEY = \
    'plone.server.registry.IAuthExtractionPlugins.active_plugins'


class IAuthExtractionPlugins(Interface):

    active_plugins = field.List(
        title=_('Active Plugins'),
        defaultFactory=list,
        value_type=field.TextLine(
            title=_('Value')
        )
    )

ACTIVE_AUTH_USER_KEY = \
    'plone.server.registry.IAuthPloneUserPlugins.active_plugins'


class IAuthPloneUserPlugins(Interface):

    active_plugins = field.List(
        title='Active Plugins',
        defaultFactory=list,
        value_type=field.TextLine(
            title='Value'
        )
    )

ACTIVE_LAYERS_KEY = 'plone.server.registry.ILayers.active_layers'


class ILayers(Interface):

    active_layers = field.List(
        title=_('Active Layers'),
        defaultFactory=list,
        value_type=field.TextLine(
            title='Value'
        )
    )


CORS_KEY = 'plone.server.registry.ICors.enabled'


class ICors(Interface):

    enabled = field.Bool(
        title=_('Enabled Cors'),
        description=_("""Enables cors on the site"""),
        default=True
    )

    allow_origin = field.List(
        title=_('Allowed Origins'),
        defaultFactory=list,
        value_type=field.TextLine(
            title='Value'
        ),
        description=_("""List of origins accepted"""),
        default=[]
    )

    allow_methods = field.List(
        title=_('Allowed Methods'),
        defaultFactory=list,
        value_type=field.TextLine(
            title='Value'
        ),
        description=_("""List of HTTP methods that are allowed by CORS"""),
        default=[]
    )

    allow_headers = field.List(
        title=_('Allowed Headers'),
        defaultFactory=list,
        value_type=field.TextLine(
            title='Value'
        ),
        description=_("""List of request headers allowed to be send by
            client"""),
        default=[]
    )

    expose_headers = field.List(
        title=_('Expose Headers'),
        defaultFactory=list,
        value_type=field.TextLine(
            title='Value'
        ),
        description=_("""List of response headers clients can access"""),
        default=[]
    )

    allow_credentials = field.Bool(
        title=_('Allow Credentials'),
        description=_("""Indicated whether the resource support user credentials
            in the request"""),
        default=True
    )

    max_age = field.TextLine(
        title=_('Max Age'),
        description=_("""Indicated how long the results of a preflight request
            can be cached"""),
        default='3660'
    )
