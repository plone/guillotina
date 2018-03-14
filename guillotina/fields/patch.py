from guillotina import configure
from guillotina import schema
from guillotina.component import query_adapter
from guillotina.json.exceptions import ValueDeserializationError
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IField
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import IPatchFieldOperation
from zope.interface import implementer


class IPatchField(IField):
    pass


@implementer(IPatchField)
class PatchField(schema.Field):

    def __init__(self, field, *args, **kwargs):
        self.field = field
        super().__init__(*args, **kwargs)

    async def set(self, obj, value):
        operation_name = value['op']
        bound_field = self.field.bind(obj)
        operation = query_adapter(bound_field, IPatchFieldOperation, name=operation_name)
        operation(obj, value['value'])
        obj._p_register()


@configure.value_deserializer(IPatchField)
def field_converter(field, value, context):
    field.field.__name__ = field.__name__
    if not isinstance(value, dict):
        raise ValueDeserializationError(field, value, 'Not an object')
    operation_name = value.get('op', 'undefined')
    operation = query_adapter(field.field, IPatchFieldOperation, name=operation_name)
    if operation is None:
        raise ValueDeserializationError(
            field, value, f'"{operation_name}" not a valid operation')
    if 'value' not in value:
        raise ValueDeserializationError(
            field, value, f'Mising value')
    return value


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='append')
class PatchListAppend:

    def __init__(self, field):
        super().__init__()
        self.field = field

    def __call__(self, context, value):
        if self.field.value_type:
            self.field.value_type.validate(value)
        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or []
            setattr(context, self.field.__name__, existing)
        existing.append(value)


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='extend')
class PatchListExtend(PatchListAppend):
    def __call__(self, context, value):
        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or []
            setattr(context, self.field.__name__, existing)
        if not isinstance(value, list):
            raise ValueDeserializationError(self.field, value, 'Not valid list')
        for item in value:
            if self.field.value_type:
                self.field.value_type.validate(item)
        existing.extend(value)


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='del')
class PatchListRemove(PatchListAppend):
    def __call__(self, context, value):
        existing = getattr(context, self.field.__name__, None)
        try:
            del existing[value]
        except IndexError:
            raise ValueDeserializationError(self.field, value, 'Not valid index value')


@configure.adapter(
    for_=IList,
    provides=IPatchFieldOperation,
    name='update')
class PatchListUpdate(PatchListAppend):
    def __call__(self, context, value):
        if 'index' not in value or 'value' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid patch value')
        if self.field.value_type:
            self.field.value_type.validate(value['value'])
        existing = getattr(context, self.field.__name__, None)
        existing[value['index']] = value['value']


@configure.adapter(
    for_=IDict,
    provides=IPatchFieldOperation,
    name='assign')
class PatchDictSet(PatchListAppend):
    def __call__(self, context, value):
        if 'key' not in value or 'value' not in value:
            raise ValueDeserializationError(self.field, value, 'Not valid patch value')

        if self.field.key_type:
            self.field.key_type.validate(value['key'])
        if self.field.value_type:
            self.field.value_type.validate(value['value'])

        existing = getattr(context, self.field.__name__, None)
        if existing is None:
            existing = self.field.missing_value or {}
            setattr(context, self.field.__name__, existing)
        existing[value['key']] = value['value']


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
