from guillotina import configure
from guillotina.behaviors.dynamic import IDynamicFields, IDynamicFieldValues
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


async def test_set_dynamic_context_behavior(custom_type_container_requester):
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
                'behavior': 'guillotina.test_package.ITestContextBehavior'
            })
        )
        assert status == 200

        # We check that the behavior is there
        response, status = await requester('GET', '/db/guillotina/item1')
        assert 'guillotina.test_package.ITestContextBehavior' in response

        # set values on behavior
        response, status = await requester(
            'PATCH',
            '/db/guillotina/item1',
            data=json.dumps({
                'guillotina.test_package.ITestContextBehavior': {
                    'foobar': 'foobar'
                }
            })
        )
        response, status = await requester('GET', '/db/guillotina/item1')
        assert 'guillotina.test_package.ITestContextBehavior' in response
        assert response['guillotina.test_package.ITestContextBehavior']['foobar'] == 'foobar'


async def test_auto_serialize_behavior(custom_type_container_requester):
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

        dotted_name = 'guillotina.test_package.ITestNoSerializeBehavior'
        # We create the behavior
        response, status = await requester(
            'PATCH',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': dotted_name
            })
        )
        assert status == 200

        # We check that the behavior is not serialized
        response, status = await requester('GET', '/db/guillotina/item1')
        assert dotted_name not in response

        # now is should be...
        response, status = await requester(
            'GET', f'/db/guillotina/item1?include={dotted_name}')
        assert dotted_name in response

        # set values on behavior
        response, status = await requester(
            'PATCH',
            '/db/guillotina/item1',
            data=json.dumps({
                dotted_name: {
                    'foobar': 'foobar'
                }
            })
        )
        response, status = await requester(
            'GET', f'/db/guillotina/item1?include={dotted_name}')
        assert dotted_name in response
        assert response[dotted_name]['foobar'] == 'foobar'


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
        assert status == 412

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
        assert status == 412

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/db/guillotina/item1'
        )
        assert 'guillotina.test_package.ITestBehavior' not in response


async def test_delete_dynamic_behavior_url(custom_type_container_requester):
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

        # We delete the behavior
        response, status = await requester(
            'DELETE',
            '/db/guillotina/item1/@behaviors/guillotina.test_package.ITestBehavior'
        )
        assert status == 200


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
        assert status == 412

        # We try to delete the behavior
        response, status = await requester(
            'DELETE',
            '/db/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 412

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


async def test_add_dynamic_fields(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            'POST', '/db/guillotina',
            data=json.dumps({
                "@type": "Item",
                "@behaviors": [IDynamicFields.__identifier__],
                "id": "foobar",
                IDynamicFields.__identifier__: {
                    "fields": {
                        "foobar": {
                            "title": "Hello field",
                            "type": "integer"
                        }
                    }
                }
            })
        )
        assert status == 201

        resp, _ = await requester(
            'GET', '/db/guillotina/foobar?include={}'.format(
                IDynamicFields.__identifier__))
        assert len(resp[IDynamicFields.__identifier__]['fields']) == 1
        resp, status = await requester(
            'GET', '/db/guillotina/foobar/@dynamic-fields')
        assert status == 200
        assert 'foobar' in resp


async def test_add_dynamic_fields_values(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            'POST', '/db/guillotina',
            data=json.dumps({
                "@type": "Item",
                "@behaviors": [IDynamicFields.__identifier__],
                "id": "foobar",
                IDynamicFields.__identifier__: {
                    "fields": {
                        "foobar": {
                            "title": "Hello field",
                            "type": "integer"
                        },
                        "foobar_date": {
                            "title": "Date field",
                            "type": "date"
                        },
                        "foobar_bool": {
                            "title": "Bool field",
                            "type": "boolean"
                        },
                        "foobar_float": {
                            "title": "Float field",
                            "type": "float"
                        },
                        "foobar_keyword": {
                            "title": "Float field",
                            "type": "keyword"
                        }
                    }
                }
            })
        )
        assert status == 201

        resp, status = await requester(
            'PATCH', '/db/guillotina/foobar', data=json.dumps({
                "@behaviors": [IDynamicFieldValues.__identifier__],
                IDynamicFieldValues.__identifier__: {
                    "values": {
                        "op": "update",
                        "value": [{
                            "key": "foobar",
                            "value": 5
                        }, {
                            "key": "foobar_date",
                            "value": '1999/01/01'
                        }, {
                            "key": "foobar_bool",
                            "value": False
                        }, {
                            "key": "foobar_keyword",
                            "value": "foobar"
                        }, {
                            "key": "foobar_float",
                            "value": 2.1
                        }]
                    }
                }
            }))
        assert status == 204
        resp, status = await requester(
            'GET', '/db/guillotina/foobar?include={}'.format(
                IDynamicFieldValues.__identifier__))
        values = resp[IDynamicFieldValues.__identifier__]['values']
        assert values['foobar'] == 5
        assert values['foobar_date'] == '1999-01-01T00:00:00'
        assert values['foobar_bool'] is False
        assert values['foobar_keyword'] == 'foobar'
        assert isinstance(values['foobar_float'], float)
        assert int(values['foobar_float']) == 2


async def test_add_dynamic_fields_invalid_type(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            'POST', '/db/guillotina',
            data=json.dumps({
                "@type": "Item",
                "@behaviors": [IDynamicFields.__identifier__],
                "id": "foobar",
                IDynamicFields.__identifier__: {
                    "fields": {
                        "foobar": {
                            "title": "Hello field",
                            "type": "integer"
                        }
                    }
                }
            })
        )
        assert status == 201

        resp, status = await requester(
            'PATCH', '/db/guillotina/foobar', data=json.dumps({
                "@behaviors": [IDynamicFieldValues.__identifier__],
                IDynamicFieldValues.__identifier__: {
                    "values": {
                        "op": "assign",
                        "value": {
                            "key": "foobar",
                            "value": 5
                        }
                    }
                }
            }))
        assert status == 204

        resp, status = await requester(
            'PATCH', '/db/guillotina/foobar', data=json.dumps({
                "@behaviors": [IDynamicFieldValues.__identifier__],
                IDynamicFieldValues.__identifier__: {
                    "values": {
                        "op": "assign",
                        "value": {
                            "key": "foobar",
                            "value": "5"
                        }
                    }
                }
            }))
        assert status == 204

        # for invalid type values
        resp, status = await requester(
            'PATCH', '/db/guillotina/foobar', data=json.dumps({
                "@behaviors": [IDynamicFieldValues.__identifier__],
                IDynamicFieldValues.__identifier__: {
                    "values": {
                        "op": "assign",
                        "value": {
                            "key": "foobar",
                            "value": "not-an-int"
                        }
                    }
                }
            }))
        assert status == 412

        # also for invalid fields
        resp, status = await requester(
            'PATCH', '/db/guillotina/foobar', data=json.dumps({
                "@behaviors": [IDynamicFieldValues.__identifier__],
                IDynamicFieldValues.__identifier__: {
                    "values": {
                        "op": "assign",
                        "value": {
                            "key": "foobar-blah",
                            "value": "5"
                        }
                    }
                }
            }))
        assert status == 412
