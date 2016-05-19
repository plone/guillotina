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
