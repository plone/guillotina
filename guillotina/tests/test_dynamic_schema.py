# -*- coding: utf-8 -*-
import json

async def test_set_dynamic_behavior(custom_type_site_requester):
    async with await custom_type_site_requester as requester:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina/',
            data=json.dumps({
                "@type": "Foobar",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201

        # We create the behavior
        response, status = await requester(
            'PATCH',
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 200

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/item1'
        )
        assert 'guillotina.behaviors.dublincore.IDublinCore' in response


async def test_create_delete_dynamic_behavior(custom_type_site_requester):
    async with await custom_type_site_requester as requester:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina/',
            data=json.dumps({
                "@type": "Foobar",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201

        # We create the behavior
        response, status = await requester(
            'PATCH',
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 200

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/item1'
        )

        assert 'guillotina.behaviors.dublincore.IDublinCore' in response

        # We delete the behavior
        response, status = await requester(
            'DELETE',
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 200

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/item1'
        )

        assert 'guillotina.behaviors.dublincore.IDublinCore' not in response


async def test_get_behaviors(custom_type_site_requester):
    async with await custom_type_site_requester as requester:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina/',
            data=json.dumps({
                "@type": "Foobar",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201

        response, status = await requester(
            'GET',
            '/guillotina/guillotina/item1/@behaviors'
        )
        assert status == 200
        assert 'guillotina.behaviors.dublincore.IDublinCore' in response['available']  # noqa
        assert 'guillotina.behaviors.dublincore.IDublinCore' in response
