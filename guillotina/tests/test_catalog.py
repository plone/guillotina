import json
import os

import pytest
from guillotina.catalog import index
from guillotina.catalog.utils import get_index_fields
from guillotina.catalog.utils import get_metadata_fields
from guillotina.component import get_adapter
from guillotina.component import query_utility
from guillotina.content import create_content
from guillotina.event import notify
from guillotina.events import ObjectModifiedEvent
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
    assert len(data) == 4  # uuid, type_name, etc always returned
    data = await util.get_data(ob, indexes=['title', 'id'])
    assert len(data) == 5

    data = await util.get_data(ob)
    assert len(data) > 9


async def test_modified_event_gathers_all_index_data(dummy_request):
    request = dummy_request  # noqa
    container = await create_content(
        'Container',
        id='guillotina',
        title='Guillotina')
    container.__name__ = 'guillotina'
    request.container = container
    ob = await create_content('Item', id='foobar')
    ob._p_oid = 'foobar'
    await notify(ObjectModifiedEvent(ob, payload={
        'title': '',
        'id': ''
    }))
    fut = index.get_request_indexer()

    assert len(fut.update['foobar']) == 5

    await notify(ObjectModifiedEvent(ob, payload={
        'creation_date': ''
    }))
    assert len(fut.update['foobar']) == 6


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


@pytest.mark.skipif(os.environ.get('DATABASE', 'DUMMY') in ('cockroachdb', 'DUMMY'),
                    reason='Not for dummy db')
async def test_query_stored_json(container_requester):
    async with container_requester as requester:
        await requester(
            'POST', '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1",
            })
        )
        await requester(
            'POST', '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item2",
                "id": "item2",
            })
        )

        conn = requester.db.storage.read_conn
        result = await conn.fetch('''
select json from {0}
where json->>'type_name' = 'Item' AND json->>'container_id' = 'guillotina'
order by json->>'id'
'''.format(requester.db.storage._objects_table_name))
        print(f'{result}')
        assert len(result) == 2
        assert json.loads(result[0]['json'])['id'] == 'item1'
        assert json.loads(result[1]['json'])['id'] == 'item2'

        result = await conn.fetch('''
select json from {0}
where json->>'id' = 'item1' AND json->>'container_id' = 'guillotina'
'''.format(requester.db.storage._objects_table_name))
        assert len(result) == 1
