from guillotina.annotations import AnnotationData
from guillotina.browser import get_physical_path
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import IRegistry
from guillotina.schema._bootstrapinterfaces import IContextAwareDefaultFactory
from zope.interface import alsoProvides
from zope.interface import implementer


REGISTRY_DATA_KEY = '_registry'


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

    def __getitem__(self, name):
        if name not in self.__dict__['schema']:
            raise KeyError(name)

        records = self.__dict__['records']
        key_name = self.__dict__['prefix'] + name
        if key_name not in records:
            return self.__dict__['schema'][name].missing_value
        return records[key_name]

    def __setitem__(self, name, value):
        if name not in self.__dict__['schema']:
            super(RecordsProxy, self).__setattr__(name, value)
        else:
            prefixed_name = self.__dict__['prefix'] + name
            self.__dict__['records'][prefixed_name] = value
            self.__dict__['records']._p_register()  # make sure we write this obj


@implementer(IRegistry, IBaseObject)
class Registry(AnnotationData):

    __name__ = '_registry'
    type_name = 'Registry'

    def __repr__(self):
        path = '/'.join([name or 'n/a' for name in get_physical_path(self)])
        return "<Registry at {path} by {mem} >".format(
            type=self.type_name,
            path=path,
            mem=id(self))

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def __setitem__(self, name, value):
        super(Registry, self).__setitem__(name, value)
        self._p_register()

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
                    proxy[name] = field.defaultFactory(self)
                else:
                    proxy[name] = field.defaultFactory()
            elif field.default is not None:
                proxy[name] = field.default
