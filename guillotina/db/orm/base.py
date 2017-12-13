from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interface import implementer
from guillotina.profile import profilable


class ObjectProperty(object):

    def __init__(self, attribute, default):
        self.attribute = attribute
        self.default = default

    def __get__(self, inst, klass):
        return getattr(inst, self.attribute, self.default)

    def __set__(self, inst, value):
        setattr(inst, self.attribute, value)

    def __delete__(self, inst, value):
        setattr(inst, self.attribute, self.default)


@implementer(IBaseObject)
class BaseObject(object):
    """
    Pure Python implmentation of Persistent base class
    """

    def __new__(cls, *args, **kw):
        inst = super(BaseObject, cls).__new__(cls)
        inst._BaseObject__annotations = {}
        return inst

    def __repr__(self):
        return "<%s %d>" % (self.__class__.__name__, id(self))

    __parent__ = ObjectProperty('_BaseObject__parent', None)
    __of__ = ObjectProperty('_BaseObject__of', None)
    __name__ = ObjectProperty('_BaseObject__name', None)
    __annotations__ = ObjectProperty('_BaseObject__annotations', None)
    __immutable_cache__ = ObjectProperty('_BaseObject__immutable_cache', False)
    __new_marker__ = ObjectProperty('_BaseObject__new_marker', False)

    # _p_:  romantic name for persistent related information
    _p_jar = ObjectProperty('_BaseObject__jar', None)
    _p_oid = ObjectProperty('_BaseObject__oid', None)
    _p_serial = ObjectProperty('_BaseObject__serial', None)

    @profilable
    def _p_register(self):
        jar = self._BaseObject__jar
        if jar is not None:
            jar.register(self)

    @profilable
    def _p_unregister(self):
        jar = self._BaseObject__jar
        if jar is not None and self._BaseObject__oid is not None:
            jar.unregister(self)

    @profilable
    def __getstate__(self):
        data = getattr(self, '__dict__')
        if data is None:
            data = {}
        for name in [k for k in data.keys() if k.startswith('_BaseObject__')]:
            del data[name]
        return data

    @profilable
    def __setstate__(self, state):
        if isinstance(state, tuple):
            inst_dict = state[0]
        else:
            inst_dict = state
        idict = getattr(self, '__dict__', None)
        if inst_dict is not None:
            idict.update(inst_dict)
