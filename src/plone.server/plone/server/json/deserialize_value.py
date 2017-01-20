# -*- coding: utf-8 -*-
from dateutil.parser import parse
from plone.server import configure
from plone.server import logger
from plone.server.interfaces import IJSONField
from plone.server.interfaces import IJSONToValue
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.interface import Interface
from zope.schema._bootstrapinterfaces import IFromUnicode
from zope.schema.interfaces import IBool
from zope.schema.interfaces import IDatetime
from zope.schema.interfaces import IDict
from zope.schema.interfaces import IField
from zope.schema.interfaces import IFrozenSet
from zope.schema.interfaces import IList
from zope.schema.interfaces import ISet
from zope.schema.interfaces import ITuple


def schema_compatible(value, schema_or_field):
    """The schema_compatible function converts any value to zope.schema
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
            schema_or_field, value))
        return None


@configure.adapter(
    for_=(dict, Interface),
    provides=IJSONToValue)
def schema_dict_converter(value, schema):
    if value == {}:
        return {}

    keys, values = zip(*value.items())
    keys = map(str, keys)
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
    return field.fromUnicode(value)


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
