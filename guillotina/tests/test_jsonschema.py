from guillotina.behaviors.dublincore import IDublinCore
from guillotina.json.utils import convert_interfaces_to_schema


def test_convert_dublin_core(dummy_guillotina):
    all_schemas = convert_interfaces_to_schema([IDublinCore])
    schema = all_schemas[IDublinCore.__identifier__]['properties']
    assert 'title' in schema
    assert 'creation_date' in schema
    assert 'tags' in schema
    assert schema['tags']['type'] == 'array'
