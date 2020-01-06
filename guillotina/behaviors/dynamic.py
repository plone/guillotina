from guillotina import configure
from guillotina import fields
from guillotina import schema
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.behaviors.instance import ContextBehavior
from guillotina.interfaces import IContentBehavior
from zope.interface import Interface


def get_all_fields(content):
    _fields = {}
    while content is not None:
        if IDynamicFields.__identifier__ in content.__behaviors__:
            behavior = IDynamicFields(content)
            for field_name, data in (behavior.fields or {}).items():
                if field_name in _fields:
                    continue
                _fields[field_name] = {
                    "title": data.get("title"),
                    "description": data.get("description"),
                    "type": data.get("type"),
                    "required": data.get("required", False),
                    "meta": data.get("meta") or {},
                }
        content = content.__parent__

    return _fields


def find_field(content, name):
    if IContentBehavior.implementedBy(content.__class__):
        content = content.context
    while content is not None:
        if IDynamicFields.__identifier__ in content.__behaviors__:
            behavior = IDynamicFields(content)
            _fields = behavior.fields or {}
            if name in _fields:
                return _fields[name]
        content = content.__parent__


class IFieldType(Interface):
    title = schema.Text(required=False)
    description = schema.Text(required=False)
    type = schema.Choice(values=["date", "integer", "text", "float", "keyword", "boolean"])
    required = schema.Bool(default=False, required=False)
    meta = schema.JSONField(
        title="Additional information on field", required=False, schema={"type": "object", "properties": {}}
    )


class IDynamicFields(Interface):
    fields = fields.PatchField(
        schema.Dict(key_type=schema.Text(), value_type=schema.Object(schema=IFieldType), max_length=1000)
    )


@configure.behavior(title="Dynamic fields", provides=IDynamicFields, for_="guillotina.interfaces.IResource")
class DynamicFieldsBehavior(ContextBehavior):
    """
    context behavior so we don't have to do an async load here...
    the data here shouldn't be very large as well
    """

    auto_serialize = False


class IDynamicFieldValues(Interface):
    values = fields.DynamicField(schema.Dict(key_type=schema.Text(), max_length=1000))


@configure.behavior(
    title="Dynamic field values", provides=IDynamicFieldValues, for_="guillotina.interfaces.IResource"
)
class DynamicFieldValuesBehavior(AnnotationBehavior):
    auto_serialize = False
    __annotations_data_key__ = "dynamicfields"
