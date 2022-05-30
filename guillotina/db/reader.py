from guillotina.db.orm.interfaces import IBaseObject
from guillotina.utils import run_async
from guillotina import app_settings

import pickle
import typing


async def reader(result: dict) -> IBaseObject:
    state = result["state"]
    if len(state) > app_settings["async_object_read_size"]:
        o = await run_async(pickle.loads, state)
    else:
        o = pickle.loads(state)
    obj = typing.cast(IBaseObject, o)
    obj.__uuid__ = result["zoid"]
    obj.__serial__ = result["tid"]
    obj.__name__ = result["id"]
    return obj
