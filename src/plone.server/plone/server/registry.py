from plone.registry import field

from zope.interface import Interface


ACTIVE_AUTH_EXTRACTION_KEY = \
    "plone.server.registry.IAuthExtractionPlugins.active_plugins"


class IAuthExtractionPlugins(Interface):

    active_plugins = field.List(
        title=u"Active Plugins",
        default=[],
        value_type=field.TextLine(title=u"Value"))

ACTIVE_AUTH_USER_KEY = \
    "plone.server.registry.IAuthPloneUserPlugins.active_plugins"


class IAuthPloneUserPlugins(Interface):

    active_plugins = field.List(
        title=u"Active Plugins",
        default=[],
        value_type=field.TextLine(title=u"Value"))

ACTIVE_LAYERS_KEY = "plone.server.registry.ILayers.active_layers"


class ILayers(Interface):

    active_layers = field.List(
        title=u"Active Layers",
        default=[],
        value_type=field.TextLine(title=u"Value"))
