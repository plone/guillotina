from guillotina._settings import app_settings
from guillotina.component import get_adapter
from guillotina.db.factory import CockroachDatabaseManager
from guillotina.db.interfaces import IDatabaseManager

import json


async def test_get_storages(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/@storages')
        assert status == 200
        assert response[0]['id'] == 'db'


async def test_get_storage(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/@storages/db')
        assert status == 200
        assert response['id'] == 'db'
        assert 'guillotina' in response['databases']


async def test_create_database(container_requester):
    async with container_requester as requester:
        response, status = await requester('POST', '/@storages/db', data=json.dumps({
            'name': 'foobar'
        }))
        assert status == 200
        response, status = await requester('GET', '/@storages/db')
        assert 'foobar' in response['databases']
        await requester('DELETE', '/@storages/db/foobar')


async def test_get_database(container_requester):
    async with container_requester as requester:
        await requester('POST', '/@storages/db', data=json.dumps({
            'name': 'foobar'
        }))
        response, status = await requester('GET', '/@storages/db/foobar')
        assert status == 200
        assert response['id'] == 'foobar'
        await requester('DELETE', '/@storages/db/foobar')


async def test_delete_database(container_requester):
    async with container_requester as requester:
        await requester('POST', '/@storages/db', data=json.dumps({
            'name': 'foobar'
        }))
        response, status = await requester('DELETE', '/@storages/db/foobar')
        assert status == 200
        response, status = await requester('GET', '/@storages/db')
        assert 'foobar' not in response['databases']


async def test_storage_impl(db, guillotina_main):
    storages = app_settings['storages']
    storage_config = storages['db']
    factory = get_adapter(guillotina_main.root, IDatabaseManager,
                          name=storage_config['storage'],
                          args=[storage_config])
    assert len(await factory.get_names()) == 0
    await factory.create('foobar')
    assert len(await factory.get_names()) == 1
    await factory.delete('foobar')
    assert len(await factory.get_names()) == 0


async def test_get_dsn_from_url():
    factory = CockroachDatabaseManager(None, {
        'dsn': 'postgresql://root@127.0.0.1:26257?sslmode=disable'
    })
    assert (factory.get_dsn('foobar') ==
        'postgresql://root@127.0.0.1:26257/foobar?sslmode=disable')
