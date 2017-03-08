# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from guillotina import configure
from guillotina.i18n import Message
from guillotina.interfaces import IValueToJson
from guillotina.schema.vocabulary import SimpleVocabulary
from guillotina.text import IRichTextValue
from zope.interface import Interface


try:
    unicode
except NameError:
    unicode = str

try:
    long
except NameError:
    long = int


def json_compatible(value):
    """The json_compatible function converts any value to JSON compatible
    data when possible, raising a TypeError for unsupported values.
    This is done by using the IJsonCompatible converters.

    Be aware that adapting the value `None` will result in a component
    lookup error unless `None` is passed in as default value.
    Because of that the `json_compatible` helper method should always be
    used for converting values that may be None.
    """
    return IValueToJson(value, None)


def encoding():
    return 'utf-8'


@configure.adapter(
    for_=Interface,
    provides=IValueToJson)
def default_converter(value):
    if value is None:
        return value

    if type(value) in (unicode, bool, int, float, long):
        return value

    raise TypeError(
        'No converter for making'
        ' {0!r} ({1}) JSON compatible.'.format(value, type(value)))


@configure.adapter(
    for_=SimpleVocabulary,
    provides=IValueToJson)
def vocabulary_converter(value):
    return [x.token for x in value]


@configure.adapter(
    for_=str,
    provides=IValueToJson)
def string_converter(value):
    return str(value, )


@configure.adapter(
    for_=list,
    provides=IValueToJson)
def list_converter(value):
    return list(map(json_compatible, value))


@configure.adapter(
    for_=tuple,
    provides=IValueToJson)
def tuple_converter(value):
    return list(map(json_compatible, value))


@configure.adapter(
    for_=frozenset,
    provides=IValueToJson)
def frozenset_converter(value):
    return list(map(json_compatible, value))


@configure.adapter(
    for_=set,
    provides=IValueToJson)
def set_converter(value):
    return list(map(json_compatible, value))


@configure.adapter(
    for_=dict,
    provides=IValueToJson)
def dict_converter(value):
    if value == {}:
        return {}

    keys, values = zip(*value.items())
    keys = map(json_compatible, keys)
    values = map(json_compatible, values)
    return dict(zip(keys, values))


@configure.adapter(
    for_=datetime,
    provides=IValueToJson)
def python_datetime_converter(value):
    try:
        return json_compatible(value.isoformat())
    except AttributeError:  # handle date problems
        return None


@configure.adapter(
    for_=date,
    provides=IValueToJson)
def date_converter(value):
    return json_compatible(value.isoformat())


@configure.adapter(
    for_=time,
    provides=IValueToJson)
def time_converter(value):
    return json_compatible(value.isoformat())


@configure.adapter(
    for_=timedelta,
    provides=IValueToJson)
def timedelta_converter(value):
    return json_compatible(value.total_seconds())


@configure.adapter(
    for_=IRichTextValue,
    provides=IValueToJson)
def richtext_converter(value):
    return {
        u'data': json_compatible(value.raw),
        u'content-type': json_compatible(value.mimeType),
        u'encoding': json_compatible(value.encoding),
    }


@configure.adapter(
    for_=Message,
    provides=IValueToJson)
def i18n_message_converter(value):
    # TODO:
    # value = translate(value, context=getRequest())
    return value
