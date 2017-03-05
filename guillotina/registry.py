# -*- coding: utf-8 -*-
from guillotina.browser import get_physical_path
from guillotina.interfaces import IRegistry

from zope.interface import alsoProvides
from guillotina import configure

from zope.schema._bootstrapinterfaces import IContextAwareDefaultFactory
from guillotina.content import Folder
import asyncio


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

    async def __setattr__(self, name, value):
        if name not in self.__dict__['schema']:
            super(RecordsProxy, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            coro = self.__dict__['records'].__setitem__(prefixed_name, value)
            if asyncio.iscoroutine(coro):
                await coro


@configure.contenttype(portal_type="Registry", schema=IRegistry)
class Registry(Folder):

    __name__ = '_registry'
    portal_type = 'Registry'

    def __repr__(self):
        path = '/'.join([name or 'n/a' for name in get_physical_path(self)])
        return "< Registry at {path} by {mem} >".format(
            type=self.portal_type,
            path=path,
            mem=id(self))

    def for_interface(self, iface, check=True, omit=(), prefix=None):
        return RecordsProxy(self, iface, prefix=prefix)

    async def register_interface(self, iface, omit=(), prefix=None):
        proxy = RecordsProxy(self, iface, prefix)
        for name in iface.names():
            if name in omit:
                continue
            field = iface[name]
            if field.defaultFactory is not None:
                if IContextAwareDefaultFactory.providedBy(field.defaultFactory):  # noqa
                    await proxy.__setattr__(name, field.defaultFactory(self))
                else:
                    await proxy.__setattr__(name, field.defaultFactory())
            elif field.default is not None:
                await proxy.__setattr__(name, field.default)
