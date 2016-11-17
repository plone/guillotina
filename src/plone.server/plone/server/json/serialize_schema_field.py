from plone.server.interfaces import IRequest
from zope.schema.interfaces import IField
from zope.interface import Interface
from zope.component import adapter
from zope.interface import implementer
from plone.server.json.interfaces import ISchemaFieldSerializeToJson
from zope.component import getMultiAdapter
from zope.schema import getFields
from zope.schema.interfaces import ICollection
from zope.schema.interfaces import IDict
from zope.schema.interfaces import IDatetime
from zope.schema.interfaces import ITime
from zope.schema.interfaces import ITextLine
from zope.schema.interfaces import IObject
from zope.schema.interfaces import IChoice
from zope.schema.interfaces import IBool
from zope.schema.interfaces import IInt
from zope.schema.interfaces import IFloat
from zope.schema.interfaces import IDate
from zope.schema.interfaces import IText
from plone.server.interfaces import IRichText
from plone.server.json.interfaces import IValueToJson
from zope.interface import implementedBy


@adapter(IField, Interface, IRequest)
@implementer(ISchemaFieldSerializeToJson)
class DefaultSchemaFieldSerializer(object):

    # Elements we won't write
    filtered_attributes = ['order', 'unique', 'defaultFactory']

    # Elements that are of the same type as the field itself
    field_type_attributes = ('min', 'max', 'default', )

    # Elements that are of the same type as the field itself, but are
    # otherwise not validated
    non_validated_field_type_attributes = ('missing_value', )

    # Attributes that contain another field. Unfortunately,
    field_instance_attributes = ('key_type', 'value_type', )

    # Fields that are always written
    forced_fields = frozenset(['default', 'missing_value'])

    def __init__(self, field, schema, request):
        self.field = field
        self.schema = schema
        self.request = request
        self.field_attributes = {}

    def __call__(self):
        result = {'type': self.field_type}
        for schema in implementedBy(self.field.__class__).flattened():
            self.field_attributes.update(getFields(schema))

        for attribute_name in sorted(self.field_attributes.keys()):
            attribute_field = self.field_attributes[attribute_name]
            if attribute_name in self.filtered_attributes:
                continue

            element_name = attribute_field.__name__
            attribute_field = attribute_field.bind(self.field)
            force = (element_name in self.forced_fields)
            value = attribute_field.get(self.field)

            # For 'default', 'missing_value' etc, we want to validate against
            # the imported field type itself, not the field type of the
            # attribute
            if element_name in self.field_type_attributes or \
                    element_name in self.non_validated_field_type_attributes:
                attribute_field = self.field

            if isinstance(value, bytes):
                text = value.decode('utf-8')
            elif isinstance(value, str):
                text = value
            elif IField.providedBy(value):
                serializer = getMultiAdapter(
                    (value, self.field, self.request),
                    ISchemaFieldSerializeToJson)
                text = serializer()
            elif value is not None and (force or value != self.field.missing_value):
                text = IValueToJson(value)

                # handle i18n
                # if isinstance(value, Message):
                #     child.set(ns('domain', I18N_NAMESPACE), value.domain)
                #     if not value.default:
                #         child.set(ns('translate', I18N_NAMESPACE), '')
                #     else:
                #         child.set(ns('translate', I18N_NAMESPACE), child.text)
                #         child.text = converter.toUnicode(value.default)
                result[attribute_name] = text

        return result

    @property
    def field_type(self):
        # Needs to be implemented on specific type
        return None


@adapter(IText, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultTextSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(ITextLine, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultTextLineSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(IFloat, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultFloatSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'number'


@adapter(IInt, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultIntSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'integer'


@adapter(IBool, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultBoolSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'boolean'


@adapter(ICollection, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultCollectionSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'array'


@adapter(IChoice, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultChoiceSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'array'


@adapter(IObject, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultObjectSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'object'


@adapter(IRichText, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultRichTextSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(IDatetime, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultDateTimeSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'datetime'


@adapter(IDate, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultDateSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'date'


@adapter(ITime, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultTimeSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'time'


@adapter(IDict, Interface, Interface)
@implementer(ISchemaFieldSerializeToJson)
class DefaultDictSchemaFieldSerializer(DefaultSchemaFieldSerializer):

    @property
    def field_type(self):
        return 'dict'
