# -*- coding: utf-8 -*-
from dateutil.parser import parse
from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import get_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.interfaces import IJSONToValue
from guillotina.schema._bootstrapinterfaces import IFromUnicode
from guillotina.schema.interfaces import IBool
from guillotina.schema.interfaces import IDate
from guillotina.schema.interfaces import IDatetime
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IField
from guillotina.schema.interfaces import IFrozenSet
from guillotina.schema.interfaces import IJSONField
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import ISet
from guillotina.schema.interfaces import ITuple
from zope.interface import Interface

import datetime


def schema_compatible(value, schema_or_field, context=None):
    """The schema_compatible function converts any value to guillotina.schema
    compatible data when possible, raising a TypeError for unsupported values.
    This is done by using the ISchemaCompatible converters.
    """
    if value is None:
        return value

    try:
        return get_adapter(schema_or_field, IJSONToValue, args=[value, context])
    except ComponentLookupError:
        raise ValueDeserializationError(
            schema_or_field, value, 'Deserializer not found for field')


@configure.value_deserializer(Interface)
def default_value_converter(schema, value, context):
    if value == {}:
        return {}

    if type(value) != dict:
        return value

    keys = [k for k in value.keys()]
    values = [k for k in value.values()]
    values = [schema_compatible(values[idx], schema[keys[idx]], context)
              for idx in range(len(keys))]
    return dict(zip(keys, values))


@configure.value_deserializer(IJSONField)
def json_dict_converter(schemafield, value, context):
    if value == {}:
        return {}

    return value

@configure.value_deserializer(for_=IField)
def default_converter(field, value, context):
    return value

@configure.value_deserializer(IBool)
def bool_converter(field, value, context):
    return bool(value)


@configure.value_deserializer(IFromUnicode)
def from_unicode_converter(field, value, context):
    return field.from_unicode(value)


@configure.value_deserializer(IList)
def list_converter(field, value, context):
    if not isinstance(value, list):
        raise ValueDeserializationError(field, value, 'Not an array')
    return [schema_compatible(item, field.value_type, context)
            for item in value]


@configure.value_deserializer(ITuple)
def tuple_converter(field, value, context):
    if not isinstance(value, list):
        raise ValueDeserializationError(field, value, 'Not an array')
    return tuple(list_converter(field, value, context))


@configure.value_deserializer(ISet)
def set_converter(field, value, context):
    if not isinstance(value, list):
        raise ValueDeserializationError(field, value, 'Not an array')
    return set(list_converter(field, value, context))


@configure.value_deserializer(IFrozenSet)
def frozenset_converter(field, value, context):
    if not isinstance(value, list):
        raise ValueDeserializationError(field, value, 'Not an array')
    return frozenset(list_converter(field, value, context))


@configure.value_deserializer(IDict)
def dict_converter(field, value, context):
    if value == {}:
        return {}

    if not isinstance(value, dict):
        raise ValueDeserializationError(field, value, 'Not an object')

    keys, values = zip(*value.items())
    keys = [schema_compatible(keys[idx], field.key_type, context)
            for idx in range(len(keys))]
    values = [schema_compatible(values[idx], field.value_type, context)
              for idx in range(len(values))]
    return dict(zip(keys, values))


@configure.value_deserializer(IDatetime)
def datetime_converter(field, value, context):
    if not isinstance(value, str):
        raise ValueDeserializationError(field, value, 'Not a string')
    return parse(value)


@configure.value_deserializer(IDate)
def date_converter(field, value, context):
    if not isinstance(value, str):
        raise ValueDeserializationError(field, value, 'Not a string')
    return datetime.datetime.strptime(value, '%Y-%m-%d').date()
