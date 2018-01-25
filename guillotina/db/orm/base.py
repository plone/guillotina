from guillotina.db.orm.interfaces import IBaseObject
from guillotina.profile import profilable
from zope.interface import implementer


class ObjectProperty(object):

    def __init__(self, attribute, default):
        self.attribute = attribute
        self.default = default

    def __get__(self, inst, klass):
        return getattr(inst, self.attribute, self.default)

    def __set__(self, inst, value):
        setattr(inst, self.attribute, value)

    def __delete__(self, inst):
        setattr(inst, self.attribute, self.default)


class DictDefaultProperty(ObjectProperty):
    def __init__(self, attribute):
        self.attribute = attribute

    def __get__(self, inst, klass):
        val = getattr(inst, self.attribute, None)
        if val is None:
            setattr(inst, self.attribute, {})
            return getattr(inst, self.attribute, None)
        return val

    def __delete__(self, inst):
        setattr(inst, self.attribute, {})


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

    __slots__ = ('__parent', '__of', '__name', '__annotations', '__immutable_cache',
                 '__new_marker')
    __parent__ = ObjectProperty('_BaseObject__parent', None)
    __of__ = ObjectProperty('_BaseObject__of', None)
    __name__ = ObjectProperty('_BaseObject__name', None)
    __annotations__ = DictDefaultProperty('_BaseObject__annotations')
    __immutable_cache__ = ObjectProperty('_BaseObject__immutable_cache', False)
    __new_marker__ = ObjectProperty('_BaseObject__new_marker', False)

    # _p_:  romantic name for persistent related information
    _p_jar = ObjectProperty('_BaseObject__jar', None)
    _p_oid = ObjectProperty('_BaseObject__oid', None)
    _p_serial = ObjectProperty('_BaseObject__serial', None)

    def _p_register(self):
        jar = self._p_jar
        if jar is not None:
            jar.register(self)

    def _p_unregister(self):
        jar = self._p_jar
        if jar is not None and self._p_oid is not None:
            jar.unregister(self)

    @profilable
    def __getstate__(self):
        return self.__dict__
