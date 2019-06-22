from guillotina.profile import profilable

import asyncpg
import pickle


@profilable
def dumps(value):
    """
    Serialize the received value using ``json.dumps``.

    :param value: dict
    :returns: str
    """
    if isinstance(value, asyncpg.Record):
        value = dict(value)
    return pickle.dumps(value)


@profilable
def loads(value):
    """
    Deserialize value using ``ujson.loads``.

    :param value: str
    :returns: output of ``json.loads``.
    """
    if value is None:
        return None
    return pickle.loads(value)
