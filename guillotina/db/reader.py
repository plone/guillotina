from guillotina.db.orm.interfaces import IBaseObject

import pickle
import typing


def reader(result: dict) -> IBaseObject:
    obj = typing.cast(IBaseObject, pickle.loads(result["state"]))
    obj.__uuid__ = result["zoid"]
    obj.__serial__ = result["tid"]
    obj.__name__ = result["id"]
    return obj
