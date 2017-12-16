from guillotina import configure
from guillotina.behaviors.properties import FunctionProperty
from guillotina.content import Item
from guillotina.content import load_cached_schema
from guillotina.tests.utils import ContainerRequesterAsyncContextManager
from zope.interface import Interface

import json
import pytest


class IFoobarType(Interface):
    pass


class FoobarType(Item):
    pass


class CustomTypeContainerRequesterAsyncContextManager(ContainerRequesterAsyncContextManager):

    async def __aenter__(self):
        configure.register_configuration(FoobarType, dict(
            schema=IFoobarType,
            type_name="Foobar",
            behaviors=[
                'guillotina.behaviors.dublincore.IDublinCore'
            ]
        ), 'contenttype')
        requester = await super(CustomTypeContainerRequesterAsyncContextManager, self).__aenter__()
        config = requester.root.app.config
        # now test it...
        configure.load_configuration(
            config, 'guillotina.tests', 'contenttype')
        config.execute_actions()
        load_cached_schema()
        return requester


@pytest.fixture(scope='function')
async def custom_type_container_requester(guillotina):
    return CustomTypeContainerRequesterAsyncContextManager(guillotina)


async def test_set_dynamic_behavior(custom_type_container_requester):
    async with custom_type_container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
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
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.test_package.ITestBehavior'
            })
        )
        assert status == 200

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/db/guillotina/item1'
        )
        assert 'guillotina.test_package.ITestBehavior' in response


async def test_create_delete_dynamic_behavior(custom_type_container_requester):
    async with custom_type_container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
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
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.test_package.ITestBehavior'
            })
        )
        assert status == 200

        # test patch again
        response, status = await requester(
            'PATCH',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.test_package.ITestBehavior'
            })
        )
        assert status == 201

        # test patch invalid...
        response, status = await requester(
            'PATCH',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.test_package.sldkflsdf'
            })
        )
        assert status == 404

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/db/guillotina/item1'
        )

        assert 'guillotina.test_package.ITestBehavior' in response

        # We delete the behavior
        response, status = await requester(
            'DELETE',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.test_package.ITestBehavior'
            })
        )
        assert status == 200

        # test delete again gives 201
        response, status = await requester(
            'DELETE',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.test_package.ITestBehavior'
            })
        )
        assert status == 201

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/db/guillotina/item1'
        )
        assert 'guillotina.test_package.ITestBehavior' not in response


async def test_get_behaviors(custom_type_container_requester):
    async with custom_type_container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Foobar",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201

        response, status = await requester(
            'GET',
            '/db/guillotina/item1/@behaviors'
        )
        assert status == 200
        assert 'guillotina.behaviors.dublincore.IDublinCore' not in response['available']  # noqa
        assert 'guillotina.behaviors.dublincore.IDublinCore' in response['static']


async def test_can_not_delete_concrete_behaviors(custom_type_container_requester):
    async with custom_type_container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
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
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 201

        # We try to delete the behavior
        response, status = await requester(
            'DELETE',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 201

        # We check that the behavior is still there
        response, status = await requester(
            'GET',
            '/db/guillotina/item1'
        )
        assert 'guillotina.behaviors.dublincore.IDublinCore' in response


def test_function_property():
    class Ob:
        pass

    def set_foo(inst, val):
        inst.foo = val

    def get_foo(inst):
        return inst.foo

    prop = FunctionProperty('foobar', get_foo, set_foo)
    ob = Ob()
    prop.__set__(ob, 'foobar')
    assert prop.__get__(ob, Ob) == 'foobar'
