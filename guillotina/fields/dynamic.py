from collections import namedtuple
from guillotina import configure
from guillotina import schema
from guillotina.component import get_adapter
from guillotina.exceptions import ComponentLookupError
from guillotina.exceptions import ValueDeserializationError
from guillotina.fields.interfaces import IDynamicField
from guillotina.fields.interfaces import IDynamicFieldOperation
from guillotina.fields.patch import field_converter
from guillotina.fields.patch import PatchDictDel
from guillotina.fields.patch import PatchDictSet
from guillotina.fields.patch import PatchDictUpdate
from guillotina.fields.patch import PatchField
from guillotina.interfaces import IJSONToValue
from guillotina.schema.interfaces import IDict
from zope.interface import implementer
from zope.interface import Interface


@implementer(IDynamicField)
class DynamicField(PatchField):
    operation_type = IDynamicFieldOperation


@configure.value_deserializer(IDynamicField)
def dynamic_field_converter(field, value, context):
    if not isinstance(value, dict) or "op" not in value:
        raise ValueDeserializationError(field, value, "Not valid payload")
    return field_converter(field, value, context)


class IDynamicType(Interface):
    """
    Used to dynamicly bind data to validate
    new values against
    """

    date = schema.Datetime(required=False)
    text = schema.Text(required=False)
    integer = schema.Int(required=False)
    float = schema.Float(required=False)
    boolean = schema.Bool(required=False)
    keyword = schema.UnionField(
        schema.List(required=False, value_type=schema.Text(), max_length=1000),
        schema.Text(required=False),
        required=False,
    )


def _validate_field(field, context, value):
    if "key" not in value or "value" not in value:
        raise ValueDeserializationError(field, value, f"Invalid data")

    from guillotina.behaviors.dynamic import find_field

    field = find_field(context, value["key"])
    # now, verify value...
    if not field:
        raise ValueDeserializationError(field, value, f"Dynamic field not found")
    field_type = field.get("type", "unknown")
    try:
        valid_type = namedtuple("temp_assign_type", [field_type])
        ob = valid_type({field_type: None})
        bound_field = IDynamicType[field_type].bind(ob)
        # validate and convert
        real_value = get_adapter(bound_field, IJSONToValue, args=[value["value"], ob])
        bound_field.validate(real_value)
        value["value"] = real_value
    except (KeyError, ComponentLookupError):
        raise ValueDeserializationError(field, value, f"Invalid type {field_type}")


@configure.adapter(for_=IDict, provides=IDynamicFieldOperation, name="assign")
class DynamicDictSet(PatchDictSet):
    def __call__(self, context, value):
        if "key" in value and "value" in value:
            _validate_field(self.field, context, value)
        return super().__call__(context, value)


@configure.adapter(for_=IDict, provides=IDynamicFieldOperation, name="update")
class DynamicDictUpdate(PatchDictUpdate):
    def __call__(self, context, value):
        if not isinstance(value, list):
            raise ValueDeserializationError(
                self.field, value, f"Invalid type patch data, must be list of updates"
            )
        for item in value:
            _validate_field(self.field, context, item)
        return super().__call__(context, value)


@configure.adapter(for_=IDict, provides=IDynamicFieldOperation, name="del")
class DynamicDictDel(PatchDictDel):
    """
    """
