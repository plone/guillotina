from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.interfaces import ITransaction
from guillotina.profile import profilable
from typing import Any
from typing import Dict
from typing import Optional, Generic, TypeVar
from zope.interface import implementer


T = TypeVar('T')


class ObjectProperty(Generic[T]):

    def __init__(self, attribute: str, default: Any) -> None:
        self.attribute = attribute
        self.default = default

    def __get__(self, inst, klass) -> T:
        return object.__getattribute__(inst, self.attribute)

    def __set__(self, inst, value: T):
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
        object.__setattr__(inst, '_BaseObject__txn', None)
        object.__setattr__(inst, '_BaseObject__uuid', None)
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
                 '__new_marker', '__txn', '__uuid', '__serial')
    __parent__: Optional[IBaseObject] = ObjectProperty[  # type: ignore
        Optional[IBaseObject]]('_BaseObject__parent', None)
    __of__: Optional[IBaseObject] = ObjectProperty[Optional[IBaseObject]](  # type: ignore
        '_BaseObject__of', None)
    __name__: Optional[str] = ObjectProperty[Optional[str]]('_BaseObject__name', None)  # type: ignore
    __immutable_cache__: bool = ObjectProperty[bool]('_BaseObject__immutable_cache', False)  # type: ignore
    __new_marker__: bool = ObjectProperty[bool]('_BaseObject__new_marker', False)  # type: ignore
    __gannotations__: Dict = DictDefaultProperty('_BaseObject__annotations')  # type: ignore
    __txn__: Optional[ITransaction] = ObjectProperty[Optional[ITransaction]](  # type: ignore
        '_BaseObject__txn', None)
    __uuid__: str = ObjectProperty[str]('_BaseObject__uuid', None)  # type: ignore
    __serial__: int = ObjectProperty[int]('_BaseObject__serial', None)  # type: ignore

    def register(self):
        txn = self.__txn__
        if txn is not None:
            txn.register(self)

    @profilable
    def __getstate__(self):
        return self.__dict__
