from guillotina.db.orm.interfaces import IBaseObject
from guillotina.profile import profilable
from typing import Any
from typing import Dict
from typing import Optional
from zope.interface import implementer


class ObjectProperty(object):

    def __init__(self, attribute: str, default: Any) -> None:
        self.attribute = attribute
        self.default = default

    def __get__(self, inst, klass) -> Any:
        return object.__getattribute__(inst, self.attribute)

    def __set__(self, inst, value):
        object.__setattr__(inst, self.attribute, value)

    def __delete__(self, inst):
        object.__setattr__(inst, self.attribute, self.default)


class DictDefaultProperty(ObjectProperty):
    def __init__(self, attribute: str) -> None:
        self.attribute = attribute

    def __get__(self, inst, klass) -> Dict:
        val = object.__getattribute__(inst, self.attribute)
        if val is None:
            object.__setattr__(inst, self.attribute, {})
            return object.__getattribute__(inst, self.attribute)
        return val

    def __delete__(self, inst):
        object.__setattr__(inst, self.attribute, {})


@implementer(IBaseObject)
class BaseObject:
    """
    Pure Python implmentation of Persistent base class
    """

    def __new__(cls, *args, **kw):
        inst = super(BaseObject, cls).__new__(cls)
        object.__setattr__(inst, '_BaseObject__annotations', {})
        object.__setattr__(inst, '_BaseObject__jar', None)
        object.__setattr__(inst, '_BaseObject__oid', None)
        object.__setattr__(inst, '_BaseObject__serial', None)
        object.__setattr__(inst, '_BaseObject__new_marker', False)
        object.__setattr__(inst, '_BaseObject__parent', None)
        object.__setattr__(inst, '_BaseObject__of', None)
        object.__setattr__(inst, '_BaseObject__name', None)
        object.__setattr__(inst, '_BaseObject__immutable_cache', False)
        return inst

    def __repr__(self):
        return "<%s %d>" % (self.__class__.__name__, id(self))

    __slots__ = ('__parent', '__of', '__name', '__annotations', '__immutable_cache',
                 '__new_marker', '__jar', '__oid', '__serial')
    __parent__: Optional['BaseObject'] = ObjectProperty('_BaseObject__parent', None)  # type: ignore
    __of__: Optional['BaseObject'] = ObjectProperty('_BaseObject__of', None)  # type: ignore
    __name__: Optional[str] = ObjectProperty('_BaseObject__name', None)  # type: ignore
    __immutable_cache__: bool = ObjectProperty('_BaseObject__immutable_cache', False)  # type: ignore
    __new_marker__ = ObjectProperty('_BaseObject__new_marker', False)
    __gannotations__: dict = DictDefaultProperty('_BaseObject__annotations')  # type: ignore

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
