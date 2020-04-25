from guillotina.profile import profilable

import asyncpg
import pickle
import typing


@profilable
def dumps(value: typing.Any) -> bytes:
    """
    Serialize the received value using ``pickle.dumps``.

    :param value: dict
    :returns: bytes
    """
    if isinstance(value, asyncpg.Record):
        value = dict(value)
    return pickle.dumps(value)


@profilable
def loads(value: bytes) -> typing.Any:
    """
    Deserialize value using ``pickle.loads``.

    :param value: bytes
    :returns: output of ``pickle.loads``.
    """
    if value is None:
        return None
    return pickle.loads(value)
