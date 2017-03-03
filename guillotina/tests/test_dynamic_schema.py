# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.content import Item
from guillotina.content import load_cached_schema
from guillotina.tests.conftest import SiteRequesterAsyncContextManager
from zope.interface import Interface

import json
import pytest


class IFoobarType(Interface):
    pass


class FoobarType(Item):
    pass


class CustomTypeSiteRequesterAsyncContextManager(SiteRequesterAsyncContextManager):

    async def __aenter__(self):
        configure.register_configuration(FoobarType, dict(
            schema=IFoobarType,
            portal_type="Foobar",
            behaviors=[]
        ), 'contenttype')
        requester = await super(CustomTypeSiteRequesterAsyncContextManager, self).__aenter__()
        config = requester.root.app.config
        # now test it...
        configure.load_configuration(
            config, 'guillotina.tests', 'contenttype')
        config.execute_actions()
        load_cached_schema()
        return requester


@pytest.fixture(scope='function')
async def custom_type_site_requester(guillotina):
    return CustomTypeSiteRequesterAsyncContextManager(guillotina)


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
