# -*- coding: utf-8 -*-


async def test_non_existing_site(site_requester):
    async with await site_requester as requester:
        response, status = await requester('GET', '/db/non')
        assert status == 404


async def test_non_existing_registry(site_requester):
    async with await site_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@registry/non')
        assert status == 404


async def test_non_existing_type(site_requester):
    async with await site_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@types/non')
        assert status == 400
        assert response['error']['type'] == 'ViewError'
