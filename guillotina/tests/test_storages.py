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
