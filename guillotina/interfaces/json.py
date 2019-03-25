from guillotina.i18n import MessageFactory
from zope.interface import Interface


_ = MessageFactory('guillotina')


class IResourceSerializeToJson(Interface):
    """Adapter to serialize a Resource into a JSON object."""

    def __init__(context, request):
        """Adapt context and request."""

    def __call__():
        """Return the json."""


class IResourceSerializeToJsonSummary(Interface):
    """Do a summary in JSON of the object.

    Adapter to serialize an object into a JSON compatible summary that
    contains only the most basic information.
    """

    def __init__(context, request):
        """Adapt context and request."""

    def __call__():
        """Return the json."""


class IFactorySerializeToJson(Interface):
    """Serialize Factory in JSON.

    The fieldset serializer multi adapter serializes the factory
    into JSON compatible python data.
    """

    def __init__(factory, request):
        """Adapt field, factory and request."""

    def __call__():
        """Return JSON compatible python data."""


class ISchemaSerializeToJson(Interface):
    """Serialize Schema in JSON.

    The fieldset serializer multi adapter serializes the schema
    into JSON compatible python data.
    """

    def __init__(schema, request):
        """Adapt field, schema and request."""

    def __call__():
        """Return JSON compatible python data."""


class ISchemaFieldSerializeToJson(Interface):
    """Serialize a schema field in JSON."""

    def __init__(field, schema, request):
        """Adapt field, schema and request."""

    def __call__():
        """Return JSON compatible python data."""


class IResourceDeserializeFromJson(Interface):
    """An adapter to deserialize a JSON object into an object in Guillotina."""


class IJSONToValue(Interface):
    """Adapter to transform JSON value to guillotina.schema value."""


class IValueToJson(Interface):
    """Convert a value to a JSON compatible data structure."""

    def __init__(value):
        """Adapt value, return json compat"""
