from guillotina.i18n import MessageFactory
from zope.interface import Interface


_ = MessageFactory('guillotina')


class IResourceSerializeToJson(Interface):
    """Adapter to serialize a Resource into a JSON object."""

    def __init__(self, context, request):
        """Adapt context and request."""

    def __call__(self):
        """Return the json."""


class IResourceSerializeToJsonSummary(Interface):
    """Do a summary in JSON of the object.

    Adapter to serialize an object into a JSON compatible summary that
    contains only the most basic information.
    """

    def __init__(self, context, request):
        """Adapt context and request."""

    def __call__(self):
        """Return the json."""


class IResourceFieldSerializer(Interface):
    """Convert the field content in JSON.

    The resource field serializer multi adapter serializes the field value into
    JSON compatible python data.
    """

    def __init__(self, field, context, request):
        """Adapt field, context and request."""

    def __call__(self):
        """Return JSON compatible python data."""


class IValueToJson(Interface):
    """Convert a value to a JSON compatible data structure."""

    def __init__(self, field, context, request):
        """Adapt field, context and request."""

    def __call__(self):
        """Return JSON compatible python data."""


class IFactorySerializeToJson(Interface):
    """Serialize Factory in JSON.

    The fieldset serializer multi adapter serializes the factory
    into JSON compatible python data.
    """

    def __init__(self, factory, request):
        """Adapt field, factory and request."""

    def __call__(self):
        """Return JSON compatible python data."""


class ISchemaSerializeToJson(Interface):
    """Serialize Schema in JSON.

    The fieldset serializer multi adapter serializes the schema
    into JSON compatible python data.
    """

    def __init__(self, schema, request):
        """Adapt field, schema and request."""

    def __call__(self):
        """Return JSON compatible python data."""


class ISchemaFieldSerializeToJson(Interface):
    """Serialize a schema field in JSON."""

    def __init__(self, field, schema, request):
        """Adapt field, schema and request."""

    def __call__(self):
        """Return JSON compatible python data."""


class IResourceDeserializeFromJson(Interface):
    """An adapter to deserialize a JSON object into an object in Guillotina."""


class IResourceFieldDeserializer(Interface):
    """Adapter to deserialize a JSON value into a field value."""

    def __init__(self, field, context, request):
        """Adapt a field, it's context and the request."""

    def __call__(self, value):
        """Convert the provided JSON value to a field value."""


class IJSONToValue(Interface):
    """Adapter to transform JSON value to guillotina.schema value."""
