from guillotina.behaviors.dublincore import IDublinCore
from guillotina.json.utils import convert_interface_to_schema


def test_convert_dublin_core():
    schema = convert_interface_to_schema(IDublinCore)
    assert 'title' in schema
    assert 'creation_date' in schema
    assert 'tags' in schema
    assert schema['tags']['type'] == 'array'
