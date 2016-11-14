# -*- coding: utf-8 -*-
from BTrees._OOBTree import OOBTree
from persistent.mapping import PersistentMapping
from plone.server import _
from plone.server.interfaces import IRegistry
from plone.server.interfaces import IResource
from zope import schema
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


class RecordsProxy(object):
    """A adapter that knows how to store data in registry.

    Each value will be stored as a primitive in the registry under a key
    that consists of the full dotted name to the field being stored.

    This class is not sufficient as an adapter factory on its own. It must
    be initialised with the schema interface in the first place. That is the
    role of the Annotations factory below.
    """

    def __init__(self, context, iface, prefix=None):
        self.__dict__['records'] = context
        self.__dict__['schema'] = iface
        if prefix is not None:
            self.__dict__['prefix'] = prefix + '.'
        else:
            self.__dict__['prefix'] = iface.__identifier__ + '.'
        alsoProvides(self, iface)

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        records = self.__dict__['records']
        key_name = self.__dict__['prefix'] + name
        if key_name not in records:
            return self.__dict__['schema'][name].missing_value

        return records[key_name]

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema']:
            super(RecordsProxy, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['records'][prefixed_name] = value


@implementer(IRegistry, IResource)
class Registry(PersistentMapping):

    __name__ = None
    __parent__ = None

    portal_type = None

    def __init__(self):
        self._data = OOBTree()
        super(Registry, self).__init__()

    def forInterface(self, iface, check=True, omit=(), prefix=None):
        return RecordsProxy(self, iface, prefix=prefix)

    def registerInterface(self, iface, omit=(), prefix=None):
        proxy = RecordsProxy(self, iface, prefix)
        for name in iface.names():
            if name in omit:
                continue
            field = iface[name]
            if field.defaultFactory is not None:
                if IContextAwareDefaultFactory.providedBy(field.defaultFactory):  # noqa
                    setattr(proxy, name, field.defaultFactory(self))
                else:
                    setattr(proxy, name, field.defaultFactory())
            elif field.default is not None:
                setattr(proxy, name, field.default)


ACTIVE_AUTH_EXTRACTION_KEY = \
    'plone.server.registry.IAuthExtractionPlugins.active_plugins'


class IAuthExtractionPlugins(Interface):

    active_plugins = schema.FrozenSet(
        title=_('Active Plugins'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title=_('Value')
        )
    )

ACTIVE_AUTH_USER_KEY = \
    'plone.server.registry.IAuthPloneUserPlugins.active_plugins'


class IAuthPloneUserPlugins(Interface):

    active_plugins = schema.FrozenSet(
        title='Active Plugins',
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        )
    )

ACTIVE_LAYERS_KEY = 'plone.server.registry.ILayers.active_layers'


class ILayers(Interface):

    active_layers = schema.FrozenSet(
        title=_('Active Layers'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        )
    )


CORS_KEY = 'plone.server.registry.ICors.enabled'


class ICors(Interface):

    enabled = schema.Bool(
        title=_('Enabled Cors'),
        description=_("""Enables cors on the site"""),
        default=False
    )

    allow_origin = schema.FrozenSet(
        title=_('Allowed Origins'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of origins accepted"""),
    )

    allow_methods = schema.FrozenSet(
        title=_('Allowed Methods'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of HTTP methods that are allowed by CORS"""),
    )

    allow_headers = schema.FrozenSet(
        title=_('Allowed Headers'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of request headers allowed to be send by
            client"""),
    )

    expose_headers = schema.FrozenSet(
        title=_('Expose Headers'),
        defaultFactory=frozenset,
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


ADDONS_KEY = 'plone.server.registry.IAddons.enabled'


class IAddons(Interface):

    enabled = schema.FrozenSet(
        title=_('Installed addons'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of enabled addons""")
    )
