from guillotina import configure
from guillotina import schema
from guillotina.addons import Addon
from guillotina.tests import utils
from guillotina.transactions import managed_transaction
from zope.interface import Interface

import json


class ITestingRegistry(Interface):
    enabled = schema.Bool(
        title="Example attribute")


@configure.addon(
    name="testaddon",
    title="Test addon")
class TestAddon(Addon):
    @classmethod
    def install(cls, container, request):
        Addon.install(container, request)

    @classmethod
    def uninstall(cls, container, request):
        Addon.uninstall(container, request)


async def test_get_root(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/')
        assert response['static_directory'] == ['static', 'module_static', 'jsapp_static']
        assert response['databases'] == ['db']
        assert response['static_file'] == ['favicon.ico']


async def test_get_database(container_requester):
    """Get the database object."""
    async with await container_requester as requester:
        response, status = await requester('GET', '/db')
        len(response['containers']) == 1


async def test_get_guillotina(container_requester):
    """Get the root guillotina container."""
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/guillotina')
        assert len(response['items']) == 0


async def test_get_contenttypes(container_requester):
    """Check list of content types."""
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@types')
        assert status == 200
        assert len(response) > 1
        assert any("Item" in s['title'] for s in response)
        assert any("Container" in s['title'] for s in response)


async def test_get_contenttype(container_requester):
    """Get a content type definition."""
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@types/Item')
        assert status == 200
        assert len(response['definitions']) == 1
        assert response['title'] == 'Item'


async def test_get_registries(container_requester):
    """Get the list of registries."""
    async with await container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@registry')
        assert status == 200
        assert len(response['value']) == 2
        assert 'guillotina.interfaces.registry.ILayers.active_layers' in response['value']


async def test_get_registry_value(container_requester):
    """Check a value from registry."""
    async with await container_requester as requester:
        response, status = await requester(
            'GET',
            '/db/guillotina/@registry/guillotina.interfaces.registry.ILayers.active_layers')
        assert response['value'] == ['guillotina.interfaces.layer.IDefaultLayer']


async def test_create_content(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201
        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('item1')
            assert obj.title == 'Item1'


async def test_create_delete_contenttype(container_requester):
    """Create and delete a content type."""
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201
        response, status = await requester('DELETE', '/db/guillotina/item1')
        assert status == 200


async def test_register_registry(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@registry',
            data=json.dumps({
                "interface": "guillotina.tests.test_api.ITestingRegistry",
                "initial_values": {
                    "enabled": True
                }
            })
        )
        assert status == 201

        response, status = await requester(
            'PATCH',
            '/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled',
            data=json.dumps({
                "value": False
            })
        )
        assert status == 204
        response, status = await requester(
            'GET',
            '/db/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled')
        assert {'value': False} == response


async def test_create_contenttype_with_date(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1",
            })
        )
        assert status == 201
        date_to_test = "2016-11-30T14:39:07.394273+01:00"
        response, status = await requester(
            'PATCH',
            '/db/guillotina/item1',
            data=json.dumps({
                "guillotina.behaviors.dublincore.IDublinCore": {
                    "creation_date": date_to_test,
                    "expiration_date": date_to_test
                }
            })
        )

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('item1')
            from guillotina.behaviors.dublincore import IDublinCore
            behavior = IDublinCore(obj)
            await behavior.load()
            assert behavior.creation_date.isoformat() == date_to_test
            assert behavior.expiration_date.isoformat() == date_to_test


async def test_create_duplicate_id(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1",
            })
        )
        assert status == 201
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1",
            })
        )
        assert status == 409
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1",
            }),
            headers={
                "OVERWRITE": "TRUE"
            }
        )
        assert status == 201


async def test_create_nested_object(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Example',
                'title': 'Item1',
                'id': 'item1',
                'categories': [{
                    'label': 'term1',
                    'number': 1.0
                }, {
                    'label': 'term2',
                    'number': 2.0
                }]
            })
        )
        assert status == 201


async def test_get_addons(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'GET', '/db/guillotina/@addons'
        )
        assert status == 200


async def test_install_invalid_addon_should_give_error(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": 'foobar'
            })
        )
        assert status == 400


async def test_install_addons(container_requester):
    id_ = 'testaddon'
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": id_
            })
        )
        assert status == 200
        assert id_ in response['installed']


async def test_install_same_addon_twice_gives_error(container_requester):
    id_ = 'testaddon'
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": id_
            })
        )
        assert status == 200
        assert id_ in response['installed']
        response, status = await requester(
            'POST',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": id_
            })
        )
        assert status == 400


async def test_uninstall_addons(container_requester):
    id_ = 'testaddon'
    async with await container_requester as requester:
        await requester(
            'POST',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": id_
            })
        )

        response, status = await requester(
            'DELETE',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": id_
            })
        )
        assert status == 200
        assert response is None


async def test_uninstall_invalid_addon(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'DELETE',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": 'foobar'
            })
        )
        assert status == 400

        response, status = await requester(
            'DELETE',
            '/db/guillotina/@addons',
            data=json.dumps({
                "id": 'testaddon'  # not installed yet...
            })
        )
        assert status == 400


async def test_get_logged_user_info(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'GET', '/db/guillotina/@user'
        )
        assert status == 200
        from guillotina.auth.users import ROOT_USER_ID
        try:
            info = response[ROOT_USER_ID]
            assert 'Managers' in info['groups']
        except KeyError:
            raise AssertionError("Code should not come here! as User `%s` "
                                 "should be in response" % ROOT_USER_ID)


async def test_not_create_content_with_invalid_id(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "lsdkfjl?#($)"
            })
        )
        assert status == 412


async def test_get_api_def(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/@apidefinition')
        assert status == 200


async def test_get_subscribers(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/@component-subscribers')
        resource = response['guillotina.interfaces.content.IResource']
        modified = resource['guillotina.interfaces.events.IObjectPermissionsModifiedEvent']
        assert modified == ['guillotina.catalog.index.security_changed']
        assert status == 200


async def test_move_content(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Folder",
                "id": "container1"
            })
        )
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Folder",
                "id": "container2"
            })
        )
        response, status = await requester(
            'POST',
            '/db/guillotina/container1',
            data=json.dumps({
                "@type": "Item",
                "id": "foobar"
            })
        )

        response, status = await requester(
            'POST',
            '/db/guillotina/container1/foobar/@move',
            data=json.dumps({
                "destination": "/container2"
            })
        )

        response, status = await requester('GET', '/db/guillotina/container2/foobar')
        assert status == 200
        response, status = await requester('GET', '/db/guillotina/container1/foobar')
        assert status == 404

        # move back with new id
        response, status = await requester(
            'POST',
            '/db/guillotina/container2/foobar/@move',
            data=json.dumps({
                "destination": "/container1",
                "new_id": "foobar_new"
            })
        )

        response, status = await requester('GET', '/db/guillotina/container1/foobar_new')
        assert status == 200
        response, status = await requester('GET', '/db/guillotina/container2/foobar')
        assert status == 404


async def test_duplicate_content(container_requester):
    async with await container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "id": "foobar1"
            })
        )
        response, status = await requester(
            'POST',
            '/db/guillotina/foobar1/@duplicate'
        )
        response, status = await requester('GET', '/db/guillotina/@ids')
        assert len(response) == 2

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar1/@duplicate',
            data=json.dumps({
                "new_id": "foobar2"
            })
        )

        response, status = await requester('GET', '/db/guillotina/@ids')
        assert len(response) == 3
        assert 'foobar2' in response
        assert 'foobar1' in response

        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                "@type": "Folder",
                "id": "folder"
            })
        )
        response, status = await requester(
            'POST',
            '/db/guillotina/foobar1/@duplicate',
            data=json.dumps({
                "new_id": "foobar",
                "destination": "/folder"
            })
        )

        response, status = await requester('GET', '/db/guillotina/folder/@ids')
        assert len(response) == 1
        assert 'foobar' in response
