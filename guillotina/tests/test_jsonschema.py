from guillotina.behaviors.dublincore import IDublinCore
from guillotina.json.utils import convert_interfaces_to_schema
from guillotina.utils import get_schema_validator
from guillotina.utils import JSONSchemaRefResolver

import jsonschema
import pytest


def test_convert_dublin_core(dummy_guillotina):
    all_schemas = convert_interfaces_to_schema([IDublinCore])
    schema = all_schemas[IDublinCore.__identifier__]["properties"]
    assert "title" in schema
    assert "creation_date" in schema
    assert "tags" in schema
    assert schema["tags"]["type"] == "array"
    assert schema["title"]["widget"] == "input"
    assert schema["description"]["widget"] == "textarea"


def test_get_json_schema_validator(dummy_guillotina):
    validator = get_schema_validator("PrincipalRole")
    validator.validate({"principal": "foobar", "role": "foobar", "setting": "Allow"})

    with pytest.raises(jsonschema.ValidationError):
        validator.validate({"principal": "foobar", "role": "foobar", "setting": "Foobar"})


def test_get_json_schema_validator_caches(dummy_guillotina):
    validator = get_schema_validator("PrincipalRole")
    assert id(validator) == id(get_schema_validator("PrincipalRole"))


def test_resolve_json_schema_type(dummy_guillotina):
    resolver = JSONSchemaRefResolver(base_uri="/", referrer=None)
    resolver.resolve_fragment(None, "/components/schemas/Behavior")
    resolver.resolve_fragment(None, "/components/schemas/Resource")

    with pytest.raises(jsonschema.exceptions.RefResolutionError):
        resolver.resolve_fragment({}, "/foo/bar/Foobar")

    with pytest.raises(jsonschema.exceptions.RefResolutionError):
        resolver.resolve_fragment({}, "/components/schemas/Foobar")

    with pytest.raises(NotImplementedError):
        resolver.resolve_remote("http://foobar.com")
