from collections import namedtuple
from guillotina import configure
from guillotina import schema
from guillotina.component import get_adapter
from guillotina.component import query_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.fields.interfaces import IPatchField
from guillotina.fields.interfaces import IPatchFieldOperation
from guillotina.interfaces import IJSONToValue
from guillotina.schema.interfaces import IArrayJSONField
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IInt
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import IObjectJSONField
from guillotina.schema.interfaces import ITuple
from guillotina.utils import apply_coroutine
from zope.interface import implementer


@implementer(IPatchField)
class PatchField(schema.Field):

    operation_type = IPatchFieldOperation

    def __init__(self, field, max_ops=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field = field
        self._bound_field = kwargs.pop("bound_field", None)
        self.required = field.required
        self.max_ops = self.field.max_ops = max_ops

    @property
    def bound_field(self):
        if self._bound_field is None:
            bound = self.field.bind(self.field.context)
            bound.__name__ = self.__name__
            return bound
        return self._bound_field

    async def set(self, obj, value):
        self.field.__name__ = self.__name__
        await apply_coroutine(self.bound_field.set, obj, value)
        obj.register()

    def bind(self, object):
        bound = super().bind(object)
        bound.field = self.field
        bound._bound_field = self.field.bind(object)
        bound._bound_field.__name__ = self.__name__
        return bound

    def validate(self, value):
        return self.bound_field.validate(value)


@configure.value_deserializer(IPatchField)
def field_converter(field, value, context):
    field.field.__name__ = field.__name__
    if isinstance(value, dict) and "op" in value:
        if not isinstance(value, dict):
            raise ValueDeserializationError(field, value, "Not an object")
        operation_name = value.get("op", "undefined")
        if operation_name == "multi":
            operation = query_adapter(field, field.operation_type, name=operation_name)
            if operation is None:
                raise ValueDeserializationError(field, value, f'"{operation_name}" not a valid operation')
            value = operation(context, value.get("value"))
        else:
            bound_field = field.field.bind(context)
            operation = query_adapter(bound_field, field.operation_type, name=operation_name)
            if operation is None:
                raise ValueDeserializationError(field, value, f'"{operation_name}" not a valid operation')
            value = operation(context, value.get("value"))
    elif isinstance(value, (dict, list)):
        value = get_adapter(field.field, IJSONToValue, args=[value, context])
    return value


@configure.adapter(for_=IPatchField, provides=IPatchFieldOperation, name="multi")
class MultiPatch:
    def __init__(self, field):
        super().__init__()
        self.field = field

    def __call__(self, context, value):
        if self.field.max_ops and len(value) > self.field.max_ops:
            raise ValueDeserializationError(
                self.field, value, f"Exceeded max allowed operations for field: {self.field.max_ops}"
            )

        bound_field = self.field.field.bind(context)
        resulting_value = None
        for op in value:
            if not isinstance(op, dict) or "op" not in op:
                raise ValueDeserializationError(self.field, value, f"{op} not a valid operation")
            resulting_value = field_converter(self.field, op, context)
            bound_field.set(context, resulting_value)
        return resulting_value


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="append")
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
            valid_type = namedtuple("temp_assign_type", [self.field.__name__])
            ob = valid_type(**{field_type.__name__: existing})
            value = get_adapter(field_type, IJSONToValue, args=[value, ob])
        return value

    def do_operation(self, existing, value):
        existing.append(value)
        return existing

    def __call__(self, context, value):
        value = self.get_value(value, None)
        if self.field.value_type:
            self.field.value_type.validate(value)
        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or []
        return self.do_operation(existing, value)


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="appendunique")
class PatchListAppendUnique(PatchListAppend):
    def do_operation(self, existing, value):
        if value not in existing:
            existing.append(value)
        return existing


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="clear")
class PatchListClear(PatchListAppend):
    def __call__(self, context, value):
        return []


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="append")
class PatchTupleAppend(PatchListAppend):
    def do_operation(self, existing, value):
        return tuple(super().do_operation(list(existing), value))


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="appendunique")
class PatchTupleAppendUnique(PatchListAppendUnique):
    def do_operation(self, existing, value):
        return tuple(super().do_operation(list(existing), value))


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="clear")
class PatchTupleClear(PatchListClear):
    def __call__(self, context, value):
        return ()


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="extend")
class PatchListExtend(PatchListAppend):
    def do_operation(self, existing, value):
        existing.extend(value)
        return existing

    def __call__(self, context, value):
        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or []
        if not isinstance(value, list):  # pragma: no cover
            raise ValueDeserializationError(self.field, value, "Not valid list")

        if self.field.max_ops and len(value) > self.field.max_ops:
            raise ValueDeserializationError(
                self.field, value, f"Exceeded max allowed operations for field: {self.field.max_ops}"
            )

        values = []
        for item in value:
            if self.field.value_type:
                item_value = self.get_value(item, None, field_type=self.field.value_type)
                self.field.value_type.validate(item_value)
                values.append(item_value)

        return self.do_operation(existing, values)


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="extendunique")
class PatchListExtendUnique(PatchListExtend):
    def do_operation(self, existing, value):
        for item in value:
            if item not in existing:
                existing.append(item)
        return existing


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="extend")
class PatchTupleExtend(PatchListExtend):
    def do_operation(self, existing, value):
        return tuple(super().do_operation(list(existing), value))


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="extendunique")
class PatchTupleExtendUnique(PatchListExtendUnique):
    def do_operation(self, existing, value):
        return tuple(super().do_operation(list(existing), value))


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="del")
class PatchListDel(PatchListAppend):
    def do_operation(self, existing, value):
        try:
            del existing[value]
        except (IndexError, TypeError):  # pragma: no cover
            raise ValueDeserializationError(self.field, value, "Not valid index value")
        return existing

    def __call__(self, context, value):
        existing = self.field.query(context) or {}
        return self.do_operation(existing, value)


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="del")
class PatchTupleDel(PatchListDel):
    def do_operation(self, existing, value):
        return tuple(super().do_operation(list(existing), value))


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="remove")
class PatchListRemove(PatchListAppend):
    def do_operation(self, existing, value):
        try:
            existing.remove(value)
        except ValueError:
            raise ValueDeserializationError(self.field, value, "{} not in value".format(value))
        return existing

    def __call__(self, context, value):
        existing = self.field.query(context) or {}
        return self.do_operation(existing, value)


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="remove")
class PatchTupleRemove(PatchListRemove):
    def do_operation(self, existing, value):
        return tuple(super().do_operation(list(existing), value))


@configure.adapter(for_=IList, provides=IPatchFieldOperation, name="update")
class PatchListUpdate(PatchListAppend):
    def do_operation(self, existing, index, result_value):
        existing[index] = result_value
        return existing

    def __call__(self, context, value):
        if "index" not in value or "value" not in value:
            raise ValueDeserializationError(self.field, value, "Not valid patch value")

        existing = self.field.query(context) or {}
        try:
            existing_item = existing[value["index"]]
        except IndexError:
            existing_item = None

        result_value = self.get_value(value["value"], existing_item)
        if self.field.value_type:
            self.field.value_type.validate(result_value)

        return self.do_operation(existing, value["index"], result_value)


@configure.adapter(for_=ITuple, provides=IPatchFieldOperation, name="update")
class PatchTupleUpdate(PatchListUpdate):
    def do_operation(self, existing, index, result_value):
        return tuple(super().do_operation(list(existing), index, result_value))


@configure.adapter(for_=IDict, provides=IPatchFieldOperation, name="assign")
class PatchDictSet(PatchListAppend):
    def __call__(self, context, value):
        if "key" not in value or "value" not in value:
            raise ValueDeserializationError(self.field, value, "Not valid patch value")

        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or {}
        existing_item = existing.get(value["key"])

        new_value = self.get_value(value["value"], existing_item)
        if self.field.key_type:
            self.field.key_type.validate(value["key"])
        if self.field.value_type:
            self.field.value_type.validate(new_value)

        existing[value["key"]] = new_value
        return existing


@configure.adapter(for_=IDict, provides=IPatchFieldOperation, name="update")
class PatchDictUpdate(PatchListAppend):
    def __call__(self, context, value):
        if not isinstance(value, list):
            raise ValueDeserializationError(
                self.field, value, f"Invalid type patch data, must be list of updates"
            )

        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or {}

        if self.field.max_ops and len(value) > self.field.max_ops:
            raise ValueDeserializationError(
                self.field, value, f"Exceeded max allowed operations for field: {self.field.max_ops}"
            )

        for item in value:
            if "key" not in item or "value" not in item:
                raise ValueDeserializationError(self.field, value, "Not valid patch value")

            existing_item = existing.get(item["key"])
            new_value = self.get_value(item["value"], existing_item)
            if self.field.key_type:
                self.field.key_type.validate(item["key"])
            if self.field.value_type:
                self.field.value_type.validate(new_value)

            existing[item["key"]] = new_value

        return existing


@configure.adapter(for_=IDict, provides=IPatchFieldOperation, name="del")
class PatchDictDel(PatchListAppend):
    def __call__(self, context, value):
        if self.field.key_type:
            self.field.key_type.validate(value)
        existing = self.field.query(context)
        try:
            del existing[value]
        except (IndexError, KeyError, TypeError):
            raise ValueDeserializationError(self.field, value, "Not valid index value")
        return existing


@configure.adapter(for_=IDict, provides=IPatchFieldOperation, name="clear")
class PatchDictClear(PatchListAppend):
    def __call__(self, context, value):
        return {}


class BasePatchIntOperation:
    def __init__(self, field):
        super().__init__()
        self.field = field


@configure.adapter(for_=IInt, provides=IPatchFieldOperation, name="inc")
class PatchIntIncrement(BasePatchIntOperation):
    def __call__(self, context, value):
        if value:
            self.field.validate(value)
        # Increment one by default
        to_increment = value or 1
        existing = self.field.query(context)
        if existing is None:
            # Get default value or assume 0
            existing = self.field.default or 0
        return existing + to_increment


@configure.adapter(for_=IInt, provides=IPatchFieldOperation, name="dec")
class PatchIntDecrement(BasePatchIntOperation):
    def __call__(self, context, value):
        if value:
            self.field.validate(value)
        # Decrement one by default
        to_decrement = value or 1
        existing = self.field.query(context)
        if existing is None:
            # Get default value or assume 0
            existing = self.field.default or 0
        return existing - to_decrement


@configure.adapter(for_=IInt, provides=IPatchFieldOperation, name="reset")
class PatchIntReset(BasePatchIntOperation):
    def __call__(self, context, value):
        # This will reset to the passed value or to the field's
        # default (if set) or 0.
        if value:
            self.field.validate(value)
        return value or self.field.default or 0


@configure.adapter(for_=IArrayJSONField, provides=IPatchFieldOperation, name="append")
class PatchJSONArrayFieldAppend(PatchListAppend):
    def do_operation(self, existing, value):
        existing.append(value)
        return existing

    def __call__(self, context, value):
        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or []

        return self.do_operation(existing, value)


@configure.adapter(for_=IArrayJSONField, provides=IPatchFieldOperation, name="appendunique")
class PatchJSONAppendUnique(PatchJSONArrayFieldAppend):
    def do_operation(self, existing, value):
        if value not in existing:
            existing.append(value)
        return existing


@configure.adapter(for_=IArrayJSONField, provides=IPatchFieldOperation, name="clear")
class PatchJSONArrayClear(PatchJSONArrayFieldAppend):
    def __call__(self, context, value):
        return []


@configure.adapter(for_=IObjectJSONField, provides=IPatchFieldOperation, name="clear")
class PatchJSONObjectClear(PatchJSONArrayFieldAppend):
    def __call__(self, context, value):
        return {}


@configure.adapter(for_=IArrayJSONField, provides=IPatchFieldOperation, name="extend")
class PatchJSONExtend(PatchJSONArrayFieldAppend):
    def do_operation(self, existing, value):
        existing.extend(value)
        return existing

    def __call__(self, context, value):
        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or []
        if not isinstance(value, list):  # pragma: no cover
            raise ValueDeserializationError(self.field, value, "Not valid list")

        if self.field.max_ops and len(value) > self.field.max_ops:
            raise ValueDeserializationError(
                self.field, value, f"Exceeded max allowed operations for field: {self.field.max_ops}"
            )

        return self.do_operation(existing, value)


@configure.adapter(for_=IArrayJSONField, provides=IPatchFieldOperation, name="assign")
class PatchJSONAssign(PatchJSONArrayFieldAppend):
    def __call__(self, context, value):
        if "key" not in value or "value" not in value:
            raise ValueDeserializationError(self.field, value, "Not valid patch value")

        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or {}

        existing[value["key"]] = value["value"]
        return existing


@configure.adapter(for_=IObjectJSONField, provides=IPatchFieldOperation, name="assign")
class PatchJSONObjetAssign(PatchJSONArrayFieldAppend):
    def __call__(self, context, value):
        if "key" not in value or "value" not in value:
            raise ValueDeserializationError(self.field, value, "Not valid patch value")

        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or {}

        existing[value["key"]] = value["value"]
        return existing


@configure.adapter(for_=IObjectJSONField, provides=IPatchFieldOperation, name="update")
class PatchJSONObjetUpdate(PatchJSONObjetAssign):
    def __call__(self, context, value):
        if not isinstance(value, list):
            raise ValueDeserializationError(
                self.field, value, f"Invalid type patch data, must be list of updates"
            )

        existing = self.field.query(context)
        if existing is None:
            existing = self.field.missing_value or {}

        if self.field.max_ops and len(value) > self.field.max_ops:
            raise ValueDeserializationError(
                self.field, value, f"Exceeded max allowed operations for field: {self.field.max_ops}"
            )

        for item in value:
            if "key" not in item or "value" not in item:
                raise ValueDeserializationError(self.field, value, "Not valid patch value")
            existing[item["key"]] = item["value"]

        return existing


@configure.adapter(for_=IArrayJSONField, provides=IPatchFieldOperation, name="del")
class PatchJSONArrayDel(PatchJSONArrayFieldAppend):
    def __call__(self, context, value):
        existing = self.field.query(context) or {}
        try:
            del existing[value]
        except (IndexError, TypeError):  # pragma: no cover
            raise ValueDeserializationError(self.field, value, "Not valid index value")
        return existing


@configure.adapter(for_=IObjectJSONField, provides=IPatchFieldOperation, name="del")
class PatchJSONObjetDel(PatchJSONArrayFieldAppend):
    def __call__(self, context, value):
        existing = self.field.query(context) or {}
        try:
            del existing[value]
        except (IndexError, KeyError, TypeError):
            raise ValueDeserializationError(self.field, value, "Not valid index value")
        return existing
