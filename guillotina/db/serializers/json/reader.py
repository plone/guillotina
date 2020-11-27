from .interfaces import IStorageDeserializer
from guillotina import configure
from guillotina.component import get_adapter
from guillotina.component import query_adapter
from guillotina.db.interfaces import IReader
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.utils import resolve_dotted_name
from zope.interface.interface import Interface

import asyncpg
import orjson


def recursive_load(d):
    if isinstance(d, dict):
        if "__class__" in d:
            adapter = query_adapter(d, IStorageDeserializer, name=d["__class__"])
            if adapter is None:
                adapter = get_adapter(d, IStorageDeserializer, name="$.AnyObjectDict")
            return adapter()
        else:
            for k, v in d.items():
                d[k] = recursive_load(v)
            return d
    elif isinstance(d, list):
        return [recursive_load(v) for v in d]
    else:
        return d


@configure.adapter(for_=(Interface), provides=IReader, name="json")
def reader(result_: asyncpg.Record) -> IBaseObject:
    result = dict(result_)
    state = orjson.loads(result["state"])
    dotted_class = state.pop("__class__")
    type_class = resolve_dotted_name(dotted_class)
    obj = type_class.__new__(type_class)

    state = recursive_load(state)

    obj.__dict__.update(state)
    obj.__uuid__ = result["zoid"]
    obj.__serial__ = result["tid"]
    obj.__name__ = result["id"]
    obj.__provides__ = obj.__providedBy__

    return obj
