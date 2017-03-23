# -*- coding: utf-8 -*-


async def test_non_existing_container(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/non')
        assert status == 404


async def test_non_existing_registry(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@registry/non')
        assert status == 404


async def test_non_existing_type(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@types/non')
        assert status == 400
        assert response['error']['type'] == 'ViewError'
