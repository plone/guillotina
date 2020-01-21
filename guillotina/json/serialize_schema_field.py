from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.fields.interfaces import IPatchField
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFileField
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.json.serialize_value import json_compatible
from guillotina.profile import profilable
from guillotina.schema import get_fields
from guillotina.schema.interfaces import IBool
from guillotina.schema.interfaces import IChoice
from guillotina.schema.interfaces import ICollection
from guillotina.schema.interfaces import IDate
from guillotina.schema.interfaces import IDatetime
from guillotina.schema.interfaces import IDecimal
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IField
from guillotina.schema.interfaces import IFloat
from guillotina.schema.interfaces import IFrozenSet
from guillotina.schema.interfaces import IInt
from guillotina.schema.interfaces import IJSONField
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import IObject
from guillotina.schema.interfaces import ISet
from guillotina.schema.interfaces import IText
from guillotina.schema.interfaces import ITextLine
from guillotina.schema.interfaces import ITime
from guillotina.schema.interfaces import ITuple
from typing import Dict
from zope.interface import implementedBy
from zope.interface import Interface


FIELDS_CACHE: dict = {}


@configure.adapter(for_=(IField, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultSchemaFieldSerializer:

    # Elements we won't write
    filtered_attributes = ["order", "unique", "defaultFactory", "required", "missing_value"]
    forced_fields = frozenset(["default", "title"])
    __name_translations: Dict[str, str] = {"readonly": "readOnly", "vocabulary": "enum"}
    name_translations: Dict[str, str] = {}

    def __init__(self, field, schema, request):
        self.field = field
        self.schema = schema
        self.request = request

    def get_field(self):
        return self.field

    @profilable
    async def __call__(self):
        return self.serialize()

    def serialize(self):
        field = self.get_field()
        result = {"type": self.field_type}
        # caching the field_attributes here improves performance dramatically
        if field.__class__ in FIELDS_CACHE:
            field_attributes = FIELDS_CACHE[field.__class__].copy()
        else:
            field_attributes = {}
            for schema in implementedBy(field.__class__).flattened():
                field_attributes.update(get_fields(schema))
            FIELDS_CACHE[field.__class__] = field_attributes
        for attribute_name in sorted(field_attributes.keys()):
            attribute_field = field_attributes[attribute_name]
            if attribute_name in self.filtered_attributes:
                continue

            value = attribute_field.get(field)
            force = attribute_field.__name__ in self.forced_fields
            if attribute_name in self.name_translations:
                attribute_name = self.name_translations[attribute_name]
            if attribute_name in self.__name_translations:
                attribute_name = self.__name_translations[attribute_name]

            info = None
            if isinstance(value, bytes):
                info = value.decode("utf-8")
            elif isinstance(value, str):
                info = value
            elif IField.providedBy(value):
                serializer = get_multi_adapter((value, field, self.request), ISchemaFieldSerializeToJson)
                info = serializer.serialize()
            elif value is not None and (force or value != field.missing_value):
                info = json_compatible(value)
            if info:
                if attribute_name == "value_type":
                    attribute_name = "items"
                result[attribute_name] = info
        if result["type"] == "object":
            if IJSONField.providedBy(field):
                result.update(field.json_schema)
            if IDict.providedBy(field):
                if "properties" not in result:
                    result["properties"] = {}
                if field.value_type:
                    field_serializer = get_multi_adapter(
                        (field.value_type, self.schema, self.request), ISchemaFieldSerializeToJson
                    )
                    result["additionalProperties"] = field_serializer.serialize()
                else:
                    result["additionalProperties"] = True
            elif IObject.providedBy(field):
                schema_serializer = get_multi_adapter((field.schema, self.request), ISchemaSerializeToJson)
                result["properties"] = schema_serializer.serialize()["properties"]
        if field.extra_values is not None:
            result.update(field.extra_values)
        if self.format:
            result["format"] = self.format
        return result

    @property
    def field_type(self):
        # Needs to be implemented on specific type if different
        return "string"

    @property
    def format(self):
        return None


@configure.adapter(for_=(IText, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultTextSchemaFieldSerializer(DefaultSchemaFieldSerializer):
    name_translations = {"max_length": "maxLength", "min_length": "minLength"}

    @property
    def field_type(self):
        return "string"


class DefaultObjectSchemaFieldSerializer(DefaultSchemaFieldSerializer):
    """
    Basic object schema field
    """

    name_translations = {"max_length": "maxProperties", "min_length": "minProperties"}


@configure.adapter(for_=(IFileField, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultFileSchemaFieldSerializer(DefaultObjectSchemaFieldSerializer):
    @property
    def field_type(self):
        return "object"


@configure.adapter(for_=(ITuple, Interface, Interface), provides=ISchemaFieldSerializeToJson)
@configure.adapter(for_=(IList, Interface, Interface), provides=ISchemaFieldSerializeToJson)
@configure.adapter(for_=(ISet, Interface, Interface), provides=ISchemaFieldSerializeToJson)
@configure.adapter(for_=(IFrozenSet, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultListFieldSchemaFieldSerializer(DefaultObjectSchemaFieldSerializer):
    name_translations = {"max_length": "maxItems", "min_length": "minItems"}

    @property
    def field_type(self):
        return "array"


@configure.adapter(for_=(IPatchField, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultPatchFieldSchemaFieldSerializer(DefaultObjectSchemaFieldSerializer):
    @property
    def name_translations(self):
        if ICollection.providedBy(self.field.field):
            return {"max_length": "maxItems", "min_length": "minItems"}
        return super().name_translations

    def get_field(self):
        return self.field.field

    @property
    def field_type(self):
        if ICollection.providedBy(self.field.field):
            return "array"
        return "object"


@configure.adapter(for_=(ICloudFileField, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultCloudFileSchemaFieldSerializer(DefaultObjectSchemaFieldSerializer):
    @property
    def field_type(self):
        return "object"


@configure.adapter(for_=(IJSONField, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultJSONFieldSerializer(DefaultObjectSchemaFieldSerializer):
    @property
    def field_type(self):
        return "object"

    def serialize(self):
        data = self.field.json_schema.copy()
        for attr_name in ("title", "description"):
            if attr_name not in data:
                value = getattr(self.field, attr_name, None)
                if value:
                    data[attr_name] = value
        return data


@configure.adapter(for_=(ITextLine, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultTextLineSchemaFieldSerializer(DefaultTextSchemaFieldSerializer):
    @property
    def field_type(self):
        return "string"


@configure.adapter(for_=(IInt, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultNumberSchemaFieldSerializer(DefaultSchemaFieldSerializer):
    name_translations = {"max": "maximum", "min": "maximum"}

    @property
    def field_type(self):
        return "number"


@configure.adapter(for_=(IFloat, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultFloatSchemaFieldSerializer(DefaultNumberSchemaFieldSerializer):
    @property
    def field_type(self):
        return "number"


@configure.adapter(for_=(IBool, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultBoolSchemaFieldSerializer(DefaultSchemaFieldSerializer):
    @property
    def field_type(self):
        return "boolean"


@configure.adapter(for_=(ICollection, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultCollectionSchemaFieldSerializer(DefaultSchemaFieldSerializer):
    @property
    def field_type(self):
        return "array"


@configure.adapter(for_=(IChoice, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultChoiceSchemaFieldSerializer(DefaultTextSchemaFieldSerializer):
    @property
    def field_type(self):
        return "string"


@configure.adapter(for_=(IObject, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultObjectFieldSchemaFieldSerializer(DefaultObjectSchemaFieldSerializer):
    @property
    def field_type(self):
        return "object"


@configure.adapter(for_=(IDatetime, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultDateTimeSchemaFieldSerializer(DefaultTextSchemaFieldSerializer):
    @property
    def field_type(self):
        return "string"

    @property
    def format(self):
        return "date-time"


@configure.adapter(for_=(IDate, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultDateSchemaFieldSerializer(DefaultTextSchemaFieldSerializer):
    @property
    def field_type(self):
        return "string"

    @property
    def format(self):
        return "date"


@configure.adapter(for_=(ITime, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultTimeSchemaFieldSerializer(DefaultTextSchemaFieldSerializer):
    @property
    def field_type(self):
        return "string"

    @property
    def format(self):
        return "time"


@configure.adapter(for_=(IDict, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultDictSchemaFieldSerializer(DefaultObjectSchemaFieldSerializer):
    @property
    def field_type(self):
        return "object"


@configure.adapter(for_=(IDecimal, Interface, Interface), provides=ISchemaFieldSerializeToJson)
class DefaultDecimalSchemaFieldSerializer(DefaultNumberSchemaFieldSerializer):
    @property
    def field_type(self):
        return "number"
