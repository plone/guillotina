# -*- coding: utf-8 -*-
from BTrees._OOBTree import OOBTree
from BTrees.Length import Length
from persistent import Persistent
from guillotina.browser import get_physical_path
from guillotina.interfaces import IRegistry
from guillotina.utils import Lazy
from zope import schema
from zope.i18nmessageid import MessageFactory
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


_ = MessageFactory('guillotina')


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


@implementer(IRegistry)
class Registry(Persistent):

    __name__ = '_registry'
    portal_type = 'Registry'

    def __init__(self):
        self._Registry__data = OOBTree()
        self.__len = Length()
        super(Registry, self).__init__()

    def __contains__(self, key):
        return key in self.__data

    @Lazy
    def _Registry__len(self):
        l = Length()
        ol = len(self.__data)
        if ol > 0:
            l.change(ol)
        self._p_changed = True
        return l

    def __len__(self):
        return self.__len()

    def __iter__(self):
        return iter(self.__data)

    def __getitem__(self, key):
        return self.__data[key]

    def get(self, key, default=None):
        return self.__data.get(key, default)

    def __setitem__(self, key, value):
        l = self.__len
        self.__data[key] = value
        l.change(1)

    def __delitem__(self, key):
        l = self.__len
        del self.__data[key]
        l.change(-1)

    has_key = __contains__

    def items(self, key=None):
        return self.__data.items(key)

    def keys(self, key=None):
        return self.__data.keys(key)

    def values(self, key=None):
        return self.__data.values(key)

    def __repr__(self):
        path = '/'.join([name or 'n/a' for name in get_physical_path(self)])
        return "< Registry at {path} by {mem} >".format(
            type=self.portal_type,
            path=path,
            mem=id(self))

    def for_interface(self, iface, check=True, omit=(), prefix=None):
        return RecordsProxy(self, iface, prefix=prefix)

    def register_interface(self, iface, omit=(), prefix=None):
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


ACTIVE_LAYERS_KEY = 'guillotina.registry.ILayers.active_layers'


class ILayers(Interface):

    active_layers = schema.FrozenSet(
        title=_('Active Layers'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        )
    )


ADDONS_KEY = 'guillotina.registry.IAddons.enabled'


class IAddons(Interface):

    enabled = schema.FrozenSet(
        title=_('Installed addons'),
        defaultFactory=frozenset,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of enabled addons""")
    )
