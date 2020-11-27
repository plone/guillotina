from guillotina import configure
from guillotina.db.interfaces import IReader
from guillotina.db.orm.interfaces import IBaseObject
from zope.interface.interface import Interface

import pickle
import typing


@configure.adapter(for_=(Interface), provides=IReader, name="pickle")
def reader(result: dict) -> IBaseObject:
    obj = typing.cast(IBaseObject, pickle.loads(result["state"]))
    obj.__uuid__ = result["zoid"]
    obj.__serial__ = result["tid"]
    obj.__name__ = result["id"]
    return obj
