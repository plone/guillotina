from collections import namedtuple
from guillotina import configure
from guillotina import schema
from guillotina.component import get_adapter
from guillotina.component import query_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.fields.interfaces import IPatchField
from guillotina.fields.interfaces import IPatchFieldOperation
from guillotina.interfaces import IJSONToValue
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IInt
from guillotina.schema.interfaces import IList
from zope.interface import implementer


@implementer(IPatchField)
class PatchField(schema.Field):

    operation_type = IPatchFieldOperation

    def __init__(self, field, *args, **kwargs):
        self.field = field
        super().__init__(*args, **kwargs)
        self.required = field.required

    def set(self, obj, value):
        bound_field = self.field.bind(obj)
        bound_field.set(obj, value)
        obj._p_register()


@configure.value_deserializer(IPatchField)
def field_converter(field, value, context):
    field.field.__name__ = field.__name__
    if isinstance(value, dict) and 'op' in value:
        if not isinstance(value, dict):
            raise ValueDeserializationError(field, value, 'Not an object')
        operation_name = value.get('op', 'undefined')
        bound_field = field.field.bind(context)
        operation = query_adapter(
            bound_field, field.operation_type, name=operation_name)
        if operation is None:
            raise ValueDeserializationError(
                field, value, f'"{operation_name}" not a valid operation')
        value = operation(context, value.get('value'))
    elif isinstance(value, (dict, list)):
        value = get_adapter(field.field, IJSONToValue, args=[value, context])
    return value


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='append')
class PatchListAppend:

    def __init__(self, field):
        super().__init__()
        self.field = field

    def get_value(self, value, existing=None, field_type=None):
        if field_type is None:
            if self.field.value_type:
                field_type = self.field.value_type
        if field_type:
            field_type.__name__ = self.field.__name__
            # for sub objects, we need to assign temp object type
            # to work with json schema correctly
            valid_type = namedtuple('temp_assign_type', [self.field.__name__])
            ob = valid_type(**{field_type.__name__: existing})
            value = get_adapter(
                field_type, IJSONToValue, args=[value, ob])
        return value

    def __call__(self, context, value):
        value = self.get_value(value, None)
        if self.field.value_type:
            self.field.value_type.validate(value)
        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or []
        existing.append(value)
        return existing


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='extend')
class PatchListExtend(PatchListAppend):
    def __call__(self, context, value):
        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or []
        if not isinstance(value, list):
            raise ValueDeserializationError(self.field, value, 'Not valid list')

        values = []
        for item in value:
            if self.field.value_type:
                item_value = self.get_value(
                    item, None, field_type=self.field.value_type)
                self.field.value_type.validate(item_value)
                values.append(item_value)
        existing.extend(values)
        return existing


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='del')
class PatchListDel(PatchListAppend):
    def __call__(self, context, value):
        existing = getattr(context, self.field.__name__, None) or {}
        try:
            del existing[value]
        except IndexError:
            raise ValueDeserializationError(self.field, value, 'Not valid index value')
        return existing


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='remove')
class PatchListRemove(PatchListAppend):
    def __call__(self, context, value):
        existing = getattr(context, self.field.__name__, None) or {}
        try:
            existing.remove(value)
        except ValueError:
            raise ValueDeserializationError(
                self.field, value, '{} not in value'.format(value))
        return existing


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='update')
class PatchListUpdate(PatchListAppend):
    def __call__(self, context, value):
        if 'index' not in value or 'value' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid patch value')

        existing = getattr(context, self.field.__name__, None) or {}
        try:
            existing_item = existing[value['index']]
        except IndexError:
            existing_item = None

        result_value = self.get_value(value['value'], existing_item)
        if self.field.value_type:
            self.field.value_type.validate(result_value)
        existing[value['index']] = result_value
        return existing


@configure.adapter(
    for_=IDict,
    provides=IPatchFieldOperation,
    name='assign')
class PatchDictSet(PatchListAppend):
    def __call__(self, context, value):
        if 'key' not in value or 'value' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid patch value')

        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or {}
        existing_item = existing.get(value['key'])

        new_value = self.get_value(value['value'], existing_item)
        if self.field.key_type:
            self.field.key_type.validate(value['key'])
        if self.field.value_type:
            self.field.value_type.validate(new_value)

        existing[value['key']] = new_value
        return existing


@configure.adapter(
    for_=IDict,
    provides=IPatchFieldOperation,
    name='update')
class PatchDictUpdate(PatchListAppend):
    def __call__(self, context, value):
        if not isinstance(value, list):
            raise ValueDeserializationError(
                self.field, value,
                f'Invalid type patch data, must be list of updates')

        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or {}

        for item in value:
            if 'key' not in item or 'value' not in item:
                raise ValueDeserializationError(self.field, value, 'Not valid patch value')

            existing_item = existing.get(item['key'])
            new_value = self.get_value(item['value'], existing_item)
            if self.field.key_type:
                self.field.key_type.validate(item['key'])
            if self.field.value_type:
                self.field.value_type.validate(new_value)

            existing[item['key']] = new_value

        return existing


@configure.adapter(
    for_=IDict,
    provides=IPatchFieldOperation,
    name='del')
class PatchDictDel(PatchListAppend):
    def __call__(self, context, value):
        if self.field.key_type:
            self.field.key_type.validate(value)
        existing = getattr(context, self.field.__name__, None)
        try:
            del existing[value]
        except (IndexError, KeyError):
            raise ValueDeserializationError(self.field, value, 'Not valid index value')
        return existing


class BasePatchIntOperation:
    def __init__(self, field):
        super().__init__()
        self.field = field


@configure.adapter(
    for_=IInt,
    provides=IPatchFieldOperation,
    name='inc')
class PatchIntIncrement(BasePatchIntOperation):
    def __call__(self, context, value):
        if value:
            self.field.validate(value)
        # Increment one by default
        to_increment = value or 1
        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            # Get default value or assume 0
            existing = self.field.default or 0
        return existing + to_increment


@configure.adapter(
    for_=IInt,
    provides=IPatchFieldOperation,
    name='dec')
class PatchIntDecrement(BasePatchIntOperation):
    def __call__(self, context, value):
        if value:
            self.field.validate(value)
        # Decrement one by default
        to_decrement = value or 1
        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            # Get default value or assume 0
            existing = self.field.default or 0
        return existing - to_decrement


@configure.adapter(
    for_=IInt,
    provides=IPatchFieldOperation,
    name='reset')
class PatchIntReset(BasePatchIntOperation):
    def __call__(self, context, value):
        # This will reset to the passed value or to the field's
        # default (if set) or 0.
        if value:
            self.field.validate(value)
        return value or self.field.default or 0
