from guillotina.db.orm.interfaces import IBaseObject
from guillotina.utils import resolve_dotted_name
import pickle
import typing


def reader(result: dict) -> IBaseObject:

    plass = resolve_dotted_name(result["type"])
    
    obj = ProtoData()
    obj.__set_plass__(plass)
    obj.ParseFromString(result["state"])

    obj.__uuid__ = result["zoid"]
    obj.__serial__ = result["tid"]
    obj.__name__ = result["id"]
    return obj
