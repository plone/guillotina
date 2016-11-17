# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone.server.json.interfaces import IValueToJson
from zope.component import adapter
from zope.i18nmessageid.message import Message
from zope.interface import implementer
from zope.interface import Interface
from plone.server.text import IRichTextValue

try:
    import Missing
    HAS_ZOPE_MISSING = True
except ImportError:
    HAS_ZOPE_MISSING = False

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


@adapter(Interface)
@implementer(IValueToJson)
def default_converter(value):
    if value is None:
        return value

    if type(value) in (unicode, bool, int, float, long):
        return value

    raise TypeError(
        'No converter for making'
        ' {0!r} ({1}) JSON compatible.'.format(value, type(value)))


@adapter(str)
@implementer(IValueToJson)
def string_converter(value):
    return str(value, )


@adapter(list)
@implementer(IValueToJson)
def list_converter(value):
    return list(map(json_compatible, value))


@adapter(PersistentList)
@implementer(IValueToJson)
def persistent_list_converter(value):
    return list_converter(value)


@adapter(tuple)
@implementer(IValueToJson)
def tuple_converter(value):
    return list(map(json_compatible, value))


@adapter(frozenset)
@implementer(IValueToJson)
def frozenset_converter(value):
    return list(map(json_compatible, value))


@adapter(set)
@implementer(IValueToJson)
def set_converter(value):
    return list(map(json_compatible, value))


@adapter(dict)
@implementer(IValueToJson)
def dict_converter(value):
    if value == {}:
        return {}

    keys, values = zip(*value.items())
    keys = map(json_compatible, keys)
    values = map(json_compatible, values)
    return dict(zip(keys, values))


@adapter(PersistentMapping)
@implementer(IValueToJson)
def persistent_mapping_converter(value):
    return dict_converter(value)


@adapter(datetime)
@implementer(IValueToJson)
def python_datetime_converter(value):
    return json_compatible(value.isoformat())


@adapter(date)
@implementer(IValueToJson)
def date_converter(value):
    return json_compatible(value.isoformat())


@adapter(time)
@implementer(IValueToJson)
def time_converter(value):
    return json_compatible(value.isoformat())


@adapter(timedelta)
@implementer(IValueToJson)
def timedelta_converter(value):
    return json_compatible(value.total_seconds())


@adapter(IRichTextValue)
@implementer(IValueToJson)
def richtext_converter(value):
    return {
        u'data': json_compatible(value.raw),
        u'content-type': json_compatible(value.mimeType),
        u'encoding': json_compatible(value.encoding),
    }


@adapter(Message)
@implementer(IValueToJson)
def i18n_message_converter(value):
    # TODO:
    # value = translate(value, context=getRequest())
    return value


if HAS_ZOPE_MISSING:
    @adapter(Missing.Value.__class__)
    @implementer(IValueToJson)
    def missing_value_converter(value):
        return None
