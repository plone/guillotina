# -*- encoding: utf-8 -*-
# flake8: noqa

import json


async def test_get_the_root(guillotina):
    requester = await guillotina
    response, status = await requester('GET', '/')
    assert response['static_file'] == ['favicon.ico']
    assert response['databases'] == ['db']
    assert response['static_directory'] == []


async def test_get_db(guillotina):
    requester = await guillotina
    response, status = await requester('GET', '/db')
    assert response['sites'] == []


async def test_get_site(site_requester):
    async with await site_requester as requester:
        response, status = await requester('GET', '/db/guillotina')
        assert response['@type'] == 'Site'


async def test_get_content(site_requester):
    async with await site_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina',
            data=json.dumps({
                '@type': 'Item',
                'id': 'hello',
                'title': 'Hola'
            }))
        assert status == 201
        response, status = await requester(
            'GET',
            '/db/guillotina/hello')
        assert status == 200


async def test_content_paths_are_correct(site_requester):
    async with await site_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina',
            data=json.dumps({
                '@type': 'Item',
                'id': 'hello',
                'title': 'Hola'
            }))
        assert status == 201
        response, status = await requester(
            'GET',
            '/db/guillotina/hello')
        assert status == 200
        assert '/db/guillotina/hello' in response['@id']
