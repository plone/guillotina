from guillotina import schema
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.component import get_multi_adapter
from guillotina.component import get_utility
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IResourceFactory
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.json.utils import convert_interfaces_to_schema
from guillotina.utils import get_schema_validator
from guillotina.utils import JSONSchemaRefResolver
from zope.interface import Interface

import jsonschema
import pytest


class IJsonSubSchemaTest(Interface):
    foo = schema.Text()
    bar = schema.Int()


class IJsonSchemaTest(Interface):
    text = schema.Text(max_length=50)
    dt = schema.Datetime()
    time = schema.Time()
    date = schema.Date()

    array = schema.List(max_length=50)
    array2 = schema.List(max_length=50, value_type=schema.Object(IJsonSubSchemaTest))
    array3 = schema.List(
        max_length=50,
        value_type=schema.JSONField({"type": "object", "properties": {"foo": {"type": "string"}}}),
    )
    ddict = schema.Dict(value_type=schema.Text(), max_length=50)
    ddict2 = schema.Dict(value_type=schema.Dict(value_type=schema.Int(), max_length=50))


def test_json_schema_text(dummy_guillotina, dummy_request):
    serializer = get_multi_adapter(
        (IJsonSchemaTest["text"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "string"
    assert data["maxLength"] == 50


def test_json_schema_dt(dummy_guillotina, dummy_request):
    serializer = get_multi_adapter(
        (IJsonSchemaTest["dt"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "string"
    assert data["format"] == "date-time"


def test_json_schema_time(dummy_guillotina, dummy_request):
    serializer = get_multi_adapter(
        (IJsonSchemaTest["time"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "string"
    assert data["format"] == "time"


def test_json_schema_date(dummy_guillotina, dummy_request):
    serializer = get_multi_adapter(
        (IJsonSchemaTest["date"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "string"
    assert data["format"] == "date"


def test_json_schema_array(dummy_guillotina, dummy_request):
    serializer = get_multi_adapter(
        (IJsonSchemaTest["array"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "array"
    assert data["maxItems"] == 50

    serializer = get_multi_adapter(
        (IJsonSchemaTest["array2"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "array"
    assert data["items"]["type"] == "object"
    assert data["maxItems"] == 50
    assert "foo" in data["items"]["properties"]
    assert "bar" in data["items"]["properties"]

    serializer = get_multi_adapter(
        (IJsonSchemaTest["array3"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "array"
    assert data["items"]["type"] == "object"
    assert data["maxItems"] == 50
    assert "foo" in data["items"]["properties"]


def test_json_schema_dict(dummy_guillotina, dummy_request):
    serializer = get_multi_adapter(
        (IJsonSchemaTest["ddict"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "object"
    assert "properties" in data
    assert data["additionalProperties"] == {"type": "string"}
    assert data["maxProperties"] == 50

    serializer = get_multi_adapter(
        (IJsonSchemaTest["ddict2"], IJsonSchemaTest, dummy_request), ISchemaFieldSerializeToJson
    )
    data = serializer.serialize()
    assert data["type"] == "object"
    assert "properties" in data
    assert data["additionalProperties"]["type"] == "object"
    assert data["additionalProperties"]["maxProperties"] == 50
    assert data["additionalProperties"]["additionalProperties"] == {"type": "number"}


def test_convert_dublin_core(dummy_guillotina):
    all_schemas = convert_interfaces_to_schema([IDublinCore])
    schema = all_schemas[IDublinCore.__identifier__]["properties"]
    assert "title" in schema
    assert "creation_date" in schema
    assert "tags" in schema
    assert schema["tags"]["type"] == "array"
    assert "maxItems" in schema["tags"]
    assert schema["tags"]["items"] == {"type": "string"}

    assert schema["creation_date"]["type"] == "string"
    assert schema["creation_date"]["format"] == "date-time"


def test_get_json_schema_validator(dummy_guillotina):
    validator = get_schema_validator("PrincipalRole")
    validator.validate({"principal": "foobar", "role": "foobar", "setting": "Allow"})

    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"principal": "foobar", "role": "foobar", "setting": "Foobar"})


def test_get_json_schema_validator_caches(dummy_guillotina):
    validator = get_schema_validator("PrincipalRole")
    assert id(validator) == id(get_schema_validator("PrincipalRole"))


async def test_serialize_factory_to_json(dummy_guillotina, dummy_request):
    factory = get_utility(IResourceFactory, name="Folder")
    serializer = get_multi_adapter((factory, dummy_request), IFactorySerializeToJson)
    data = await serializer()
    assert data["properties"]["guillotina.behaviors.dublincore.IDublinCore"] == {
        "$ref": "#/components/schemas/guillotina.behaviors.dublincore.IDublinCore"
    }


async def test_resolve_json_schema_type(dummy_guillotina):
    resolver = JSONSchemaRefResolver(base_uri="/", referrer=None)
    resolver.resolve_fragment(None, "/components/schemas/Behavior")
    resolver.resolve_fragment(None, "/components/schemas/Resource")

    with pytest.raises(jsonschema.exceptions.RefResolutionError):
        resolver.resolve_fragment({}, "/foo/bar/Foobar")

    with pytest.raises(jsonschema.exceptions.RefResolutionError):
        resolver.resolve_fragment({}, "/components/schemas/Foobar")

    with pytest.raises(NotImplementedError):
        resolver.resolve_remote("http://foobar.com")
