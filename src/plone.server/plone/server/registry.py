# -*- coding: utf-8 -*-
from zope import schema
from plone.server import _
from zope.interface import Interface


ACTIVE_AUTH_EXTRACTION_KEY = \
    'plone.server.registry.IAuthExtractionPlugins.active_plugins'


class IAuthExtractionPlugins(Interface):

    active_plugins = schema.List(
        title=_('Active Plugins'),
        defaultFactory=list,
        value_type=schema.TextLine(
            title=_('Value')
        )
    )

ACTIVE_AUTH_USER_KEY = \
    'plone.server.registry.IAuthPloneUserPlugins.active_plugins'


class IAuthPloneUserPlugins(Interface):

    active_plugins = schema.List(
        title='Active Plugins',
        defaultFactory=list,
        value_type=schema.TextLine(
            title='Value'
        )
    )

ACTIVE_LAYERS_KEY = 'plone.server.registry.ILayers.active_layers'


class ILayers(Interface):

    active_layers = schema.List(
        title=_('Active Layers'),
        defaultFactory=list,
        value_type=schema.TextLine(
            title='Value'
        )
    )


CORS_KEY = 'plone.server.registry.ICors.enabled'


class ICors(Interface):

    enabled = schema.Bool(
        title=_('Enabled Cors'),
        description=_("""Enables cors on the site"""),
    )

    allow_origin = schema.List(
        title=_('Allowed Origins'),
        defaultFactory=list,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of origins accepted"""),
    )

    allow_methods = schema.List(
        title=_('Allowed Methods'),
        defaultFactory=list,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of HTTP methods that are allowed by CORS"""),
    )

    allow_headers = schema.List(
        title=_('Allowed Headers'),
        defaultFactory=list,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of request headers allowed to be send by
            client"""),
    )

    expose_headers = schema.List(
        title=_('Expose Headers'),
        defaultFactory=list,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of response headers clients can access"""),
    )

    allow_credentials = schema.Bool(
        title=_('Allow Credentials'),
        description=_("""Indicated whether the resource support user credentials
            in the request"""),
    )

    max_age = schema.TextLine(
        title=_('Max Age'),
        description=_("""Indicated how long the results of a preflight request
            can be cached"""),
    )
