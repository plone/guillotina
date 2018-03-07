from guillotina.exceptions import DeserializationError
from guillotina.exceptions import ValueDeserializationError


async def test_non_existing_container(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/non')
        assert status == 404


async def test_non_existing_registry(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@registry/non')
        assert status == 404


async def test_non_existing_type(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@types/non')
        assert status == 404


def test_deserialization_error_formats_error():
    error = DeserializationError([{
        'error': 'Foobar',
        'field': 'foobar_field'
    }])
    assert 'foobar_field' in str(error)


def test_value_serialization_error():
    error = ValueDeserializationError('Foo', 'Bar', 'Something wrong')
    assert error.field == 'Foo'
    assert error.value == 'Bar'
