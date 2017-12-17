from guillotina.catalog.utils import get_index_fields
from guillotina.catalog.utils import get_metadata_fields
from guillotina.component import get_adapter
from guillotina.component import query_utility
from guillotina.content import create_content
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import ISecurityInfo
from guillotina.tests import utils as test_utils


def test_indexed_fields(dummy_guillotina, loop):
    fields = get_index_fields('Item')
    assert 'uuid' in fields
    assert 'path' in fields
    assert 'title' in fields
    assert 'creation_date' in fields
    metadata = get_metadata_fields('Example')
    assert len(metadata) == 1


async def test_get_index_data(dummy_request):
    request = dummy_request  # noqa

    container = await create_content(
        'Container',
        id='guillotina',
        title='Guillotina')
    container.__name__ = 'guillotina'

    ob = await create_content('Item', id='foobar')

    data = ICatalogDataAdapter(ob)
    fields = await data()
    assert 'type_name' in fields
    assert 'uuid' in fields
    assert 'path' in fields
    assert 'title' in fields


async def test_registered_base_utility(dummy_request):
    util = query_utility(ICatalogUtility)
    assert util is not None


async def test_get_security_data(dummy_request):
    request = dummy_request  # noqa
    ob = test_utils.create_content()
    adapter = get_adapter(ob, ISecurityInfo)
    data = adapter()
    assert 'access_users' in data
    assert 'access_roles' in data


async def test_get_data_uses_indexes_param(dummy_request):
    util = query_utility(ICatalogUtility)
    request = dummy_request  # noqa
    container = await create_content(
        'Container',
        id='guillotina',
        title='Guillotina')
    container.__name__ = 'guillotina'
    ob = await create_content('Item', id='foobar')
    data = await util.get_data(ob, indexes=['title'])
    assert len(data) == 4  # uuid, type_name, id, etc always returned

    data = await util.get_data(ob)
    assert len(data) > 8


async def test_search_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@search')
        assert status == 200


async def test_search_post_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester('POST', '/db/guillotina/@search', data='{}')
        assert status == 200


async def test_reindex_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester('POST', '/db/guillotina/@catalog-reindex', data='{}')
        assert status == 200


async def test_async_reindex_endpoint(container_requester):
    async with container_requester as requester:
        response, status = await requester('POST', '/db/guillotina/@async-catalog-reindex', data='{}')
        assert status == 200


async def test_create_catalog(container_requester):
    async with container_requester as requester:
        response, status = await requester('POST', '/db/guillotina/@catalog', data='{}')
        assert status == 200
        response, status = await requester('DELETE', '/db/guillotina/@catalog')
        assert status == 200
