# -*- coding: utf-8 -*-
from guillotina.browser import get_physical_path
from guillotina.content import Folder
from guillotina.interfaces import IRegistry
from zope.interface import alsoProvides
from zope.interface import implementer_only
from zope.interface import Interface
from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory


try:
    from guillotinadb.orm.interfaces import IBaseObject
except ImportError:
    class IBaseObject(Interface):
        pass  # face interface to use instead that NOTHING should implement...


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

    async def async_get(self, name):
        key_name = self.__dict__['prefix'] + name
        return await self.__dict__['records'][key_name]

    async def async_set(self, name, value):
        prefixed_name = self.__dict__['prefix'] + name
        await self.__dict__['records'].__setitem__(prefixed_name, value)

    def __getattr__(self, name):
        if name not in self.__dict__['schema']:
            raise AttributeError(name)

        records = self.__dict__['records']
        key_name = self.__dict__['prefix'] + name
        if key_name not in records:
            return self.__dict__['schema'][name].missing_value
        return records.__getattr__(key_name)

    def __setattr__(self, name, value):
        if name not in self.__dict__['schema']:
            super(RecordsProxy, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['records'][prefixed_name].__setattr__(prefixed_name, value)


@implementer_only(IRegistry, IBaseObject)
class Registry(Folder):

    __name__ = '_registry'
    portal_type = 'Registry'

    def __init__(self, id='_registry'):
        super(Registry, self).__init__(id)

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
                    proxy.__setattr__(name, field.defaultFactory(self))
                else:
                    proxy.__setattr__(name, field.defaultFactory())
            elif field.default is not None:
                proxy.__setattr__(name, field.default)
