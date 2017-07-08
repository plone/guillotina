from guillotina import schema
from guillotina.utils import get_dotted_name

import logging


logger = logging.getLogger('guillotina')


_type_mappings = {
    schema.TextLine: 'string',
    schema.Text: 'string',
    schema.Int: 'integer',
    schema.Float: 'float',
    schema.Bool: 'boolean',
    schema.Datetime: 'string',
    schema.Date: 'string'
}
_array_types = {
    schema.List,
    schema.Set,
    schema.Tuple
}
_prop_mappings = {
    'max_length': 'maxLength',
    'min_length': 'minLength'
}


def convert_field_to_schema(field):
    field_type = type(field)

    props = {
        "required": field.required,
        "title": field.title
    }

    if field_type in _array_types:
        props.update({
            "type": "array",
            "items": {
                "type": _type_mappings[type(field.value_type)]
            }
        })
    elif field_type in _type_mappings:
        props.update({
            "type": _type_mappings[field_type]
        })
    else:
        logger.warning('Could not convert field {} of {} into json schema'.format(
            field.__name__, get_dotted_name(field.interface)
        ))
        return
    for prop_name, schema_name in _prop_mappings.items():
        val = getattr(field, prop_name, None)
        if val is not None:
            props[schema_name] = val
    return props


def convert_interface_to_schema(iface):
    properties = {}
    for name in iface.names():
        field = iface[name]
        try:
            props = convert_field_to_schema(field)
        except Exception:
            logger.warning('Error converting {} of {} into json schema'.format(
                name, get_dotted_name(iface)
            ))
        if props is not None:
            properties[name] = props
    return properties


def convert_interfaces_to_schema(interfaces):
    properties = {}
    for iface in interfaces:
        properties[get_dotted_name(iface)] = {
            "type": "object",
            "properties": convert_interface_to_schema(iface)
        }
    return properties
