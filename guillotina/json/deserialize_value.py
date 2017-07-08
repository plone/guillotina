# -*- coding: utf-8 -*-
from dateutil.parser import parse
from guillotina import configure
from guillotina import logger
from guillotina.component import ComponentLookupError
from guillotina.component import getMultiAdapter
from guillotina.interfaces import IJSONToValue
from guillotina.schema._bootstrapinterfaces import IFromUnicode
from guillotina.schema.interfaces import IBool
from guillotina.schema.interfaces import IDatetime
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IField
from guillotina.schema.interfaces import IFrozenSet
from guillotina.schema.interfaces import IJSONField
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import ISet
from guillotina.schema.interfaces import ITuple
from zope.interface import Interface


def schema_compatible(value, schema_or_field):
    """The schema_compatible function converts any value to guillotina.schema
    compatible data when possible, raising a TypeError for unsupported values.
    This is done by using the ISchemaCompatible converters.
    """
    if value is None:
        return value

    try:
        return getMultiAdapter((value, schema_or_field), IJSONToValue)
    except ComponentLookupError:
        logger.error((u'Deserializer not found for field type '
                      u'"{0:s}" with value "{1:s}" and it was '
                      u'deserialized to None.').format(
            repr(schema_or_field), value))
        return None


@configure.adapter(
    for_=(dict, Interface),
    provides=IJSONToValue)
def schema_dict_converter(value, schema):
    if value == {}:
        return {}

    keys = [k for k in value.keys()]
    values = [k for k in value.values()]
    values = [schema_compatible(values[idx], schema[keys[idx]])
              for idx in range(len(keys))]
    return dict(zip(keys, values))


@configure.adapter(
    for_=(dict, IJSONField),
    provides=IJSONToValue)
def json_dict_converter(value, schemafield):
    if value == {}:
        return {}

    return value


@configure.adapter(
    for_=(Interface, IField),
    provides=IJSONToValue)
def default_converter(value, field):
    return value


@configure.adapter(
    for_=(Interface, IBool),
    provides=IJSONToValue)
def bool_converter(value, field):
    return bool(value)


@configure.adapter(
    for_=(Interface, IFromUnicode),
    provides=IJSONToValue)
def from_unicode_converter(value, field):
    return field.from_unicode(value)


@configure.adapter(
    for_=(list, IList),
    provides=IJSONToValue)
def list_converter(value, field):
    return [schema_compatible(item, field.value_type)
            for item in value]


@configure.adapter(
    for_=(list, ITuple),
    provides=IJSONToValue)
def tuple_converter(value, field):
    return tuple(list_converter(value, field))


@configure.adapter(
    for_=(list, ISet),
    provides=IJSONToValue)
def set_converter(value, field):
    return set(list_converter(value, field))


@configure.adapter(
    for_=(list, IFrozenSet),
    provides=IJSONToValue)
def frozenset_converter(value, field):
    return frozenset(list_converter(value, field))


@configure.adapter(
    for_=(dict, IDict),
    provides=IJSONToValue)
def dict_converter(value, field):
    if value == {}:
        return {}

    keys, values = zip(*value.items())
    keys = [schema_compatible(keys[idx], field.key_type)
            for idx in range(len(keys))]
    values = [schema_compatible(values[idx], field.value_type)
              for idx in range(len(values))]
    return dict(zip(keys, values))


@configure.adapter(
    for_=(str, IDatetime),
    provides=IJSONToValue)
def datetime_converter(value, field):
    return parse(value)
