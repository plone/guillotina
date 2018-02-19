# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from guillotina import configure
from guillotina.component import query_adapter
from guillotina.i18n import Message
from guillotina.interfaces import IValueToJson
from guillotina.profile import profilable
from guillotina.schema.vocabulary import SimpleVocabulary


_MISSING = object()


@profilable
def json_compatible(value):
    if value is None:
        return value

    type_ = type(value)
    if type_ in (str, bool, int, float):
        return value

    result_value = query_adapter(value, IValueToJson, default=_MISSING)
    if result_value is _MISSING:
        raise TypeError(
            'No converter for making'
            ' {0!r} ({1}) JSON compatible.'.format(value, type(value)))
    else:
        return result_value


@configure.value_serializer(SimpleVocabulary)
def vocabulary_converter(value):
    return [x.token for x in value]


@configure.value_serializer(str)
def string_converter(value):
    return str(value)


@configure.value_serializer(list)
def list_converter(value):
    return list(map(json_compatible, value))


@configure.value_serializer(tuple)
def tuple_converter(value):
    return list(map(json_compatible, value))


@configure.value_serializer(frozenset)
def frozenset_converter(value):
    return list(map(json_compatible, value))


@configure.value_serializer(set)
def set_converter(value):
    return list(map(json_compatible, value))


@configure.value_serializer(dict)
def dict_converter(value):
    if value == {}:
        return {}

    keys, values = zip(*value.items())
    keys = map(json_compatible, keys)
    values = map(json_compatible, values)
    return dict(zip(keys, values))


@configure.value_serializer(datetime)
def python_datetime_converter(value):
    try:
        return value.isoformat()
    except AttributeError:  # handle date problems
        return None


@configure.value_serializer(date)
def date_converter(value):
    return value.isoformat()


@configure.value_serializer(time)
def time_converter(value):
    return value.isoformat()


@configure.value_serializer(timedelta)
def timedelta_converter(value):
    return value.total_seconds()


@configure.value_serializer(Message)
def i18n_message_converter(value):
    # TODO:
    # value = translate(value, context=getRequest())
    return value


@configure.value_serializer(Decimal)
def decimal_converter(value):
    return str(value)
