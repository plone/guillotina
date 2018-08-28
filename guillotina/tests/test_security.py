from guillotina.security.utils import get_principals_with_access_content
from guillotina.security.utils import get_roles_with_access_content
from guillotina.security.utils import settings_for_object
from guillotina.tests import utils
from guillotina.transactions import managed_transaction
from guillotina.auth.users import GuillotinaUser

import json


async def test_get_guillotina(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@sharing')
        assert response['local']['prinrole']['root']['guillotina.ContainerAdmin'] == 'Allow'
        assert response['local']['prinrole']['root']['guillotina.Owner'] == 'Allow'


async def test_database_root_has_none_parent(container_requester):
    async with container_requester as requester:
        # important for security checks to not inherit...
        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        assert root.__parent__ is None


async def test_set_local_guillotina(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'user1',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'AllowSingle'
                }]
            })
        )
        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'testing'
            })
        )
        assert status == 201

        response, status = await requester(
            'GET', '/db/guillotina/testing/@sharing')

        assert len(response['inherit']) == 1
        assert response['inherit'][0]['prinrole']['root']['guillotina.ContainerAdmin'] == 'Allow'
        assert response['inherit'][0]['prinrole']['root']['guillotina.Owner'] == 'Allow'
        assert 'Anonymous User' not in response['inherit'][0]['prinrole']
        assert response['inherit'][0]['prinperm']['user1']['guillotina.AccessContent'] == 'AllowSingle'  # noqa

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)

        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            testing_object = await container.async_get('testing')

            # Check the access users/roles
            principals = get_principals_with_access_content(testing_object, request)
            assert principals == ['root']
            roles = get_roles_with_access_content(testing_object, request)
            assert roles == ['guillotina.Reader', 'guillotina.Reviewer', 'guillotina.Owner',
                             'guillotina.Editor', 'guillotina.ContainerAdmin']
            data = settings_for_object(testing_object)
            assert 'testing' in data[0]

        # Now we add the user1 with inherit on the container
        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'user1',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'Allow'
                }]
            })
        )

        root = await utils.get_root(request)

        async with managed_transaction(request=request, abort_when_done=True):
            # need to retreive objs again from db since they changed
            container = await root.async_get('guillotina')
            testing_object = await container.async_get('testing')
            principals = get_principals_with_access_content(testing_object, request)
            assert len(principals) == 2
            assert 'user1' in principals

        # Now we add the user1 with deny on the object
        response, status = await requester(
            'POST',
            '/db/guillotina/testing/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'user1',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'Deny'
                }]
            })
        )
        # need to retreive objs again from db since they changed
        root = await utils.get_root(request)

        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            testing_object = await container.async_get('testing')
            principals = get_principals_with_access_content(testing_object, request)
            assert principals == ['root']


async def test_sharing_prinrole(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'prinrole': [{
                    'principal': 'user1',
                    'role': 'guillotina.Reader',
                    'setting': 'AllowSingle'
                }]
            })
        )
        assert status == 200

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)

        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            assert 'user1' in container.__acl__['prinrole']._bycol


async def test_sharing_roleperm(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'roleperm': [{
                    'permission': 'guillotina.ViewContent',
                    'role': 'guillotina.Reader',
                    'setting': 'AllowSingle'
                }]
            })
        )
        assert status == 200

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)

        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            assert 'guillotina.Reader' in container.__acl__['roleperm']._bycol


async def test_canido(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'GET', '/db/guillotina/@canido?permission=guillotina.ViewContent')
        assert status == 200
        assert response


async def test_canido_mutliple(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'GET', '/db/guillotina/@canido',
            params={
                'permissions': 'guillotina.ViewContent,guillotina.ModifyContent'
            })
        assert status == 200
        assert response['guillotina.ViewContent']
        assert response['guillotina.ModifyContent']


async def test_inherit(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'testing'
            }))
        assert status == 201

        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'prinrole': [{
                    'principal': 'user1',
                    'role': 'guillotina.Reader',
                    'setting': 'Allow'
                }]
            }))

        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/@sharing',
            data=json.dumps({
                'perminhe': [{
                    'permission': 'guillotina.ViewContent',
                    'setting': 'Deny'
                }]
            }))
        assert status == 200

        response, status = await requester(
            'GET',
            '/db/guillotina/testing/@all_permissions')
        assert status == 200

        request = utils.get_mocked_request(requester.db)
        container = await utils.get_container(requester, request)
        content = await container.async_get('testing')

        user = GuillotinaUser(request)
        user.id = 'user1'

        utils.login(request, user)

        assert request.security.check_permission('guillotina.ViewContent',
                                                 request.container)
        assert not request.security.check_permission(
            'guillotina.ViewContent',
            content)

        response, status = await requester(
            'GET',
            '/db/guillotina/testing')
        assert status == 401

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/@sharing',
            data=json.dumps({
                'roleperm': [{
                    'permission': 'guillotina.ViewContent',
                    'role': 'guillotina.Manager',
                    'setting': 'Allow'
                }]
            }))
        assert status == 200

        response, status = await requester(
            'GET',
            '/db/guillotina/testing')
        assert status == 200


async def test_allowsingle(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'testing'
            }))
        assert status == 201

        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'group1',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'AllowSingle'
                }]
            }))

        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'group2',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'Allow'
                }]
            }))

        assert status == 200

        request = utils.get_mocked_request(requester.db)
        container = await utils.get_container(requester, request)
        content = await container.async_get('testing')

        user = GuillotinaUser(request)
        user.id = 'user1'
        user._groups = ['group1', 'group2']

        utils.login(request, user)

        assert request.security.check_permission('guillotina.AccessContent',
                                                 request.container)
        assert request.security.check_permission('guillotina.AccessContent',
                                                 content)

        user = GuillotinaUser(request)
        user.id = 'user2'
        user._groups = ['group1']

        utils.login(request, user)

        assert request.security.check_permission('guillotina.AccessContent',
                                                 request.container)
        assert not request.security.check_permission(
            'guillotina.AccessContent', content)


async def test_allowsingle2(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Folder',
                'id': 'testing'
            }))
        assert status == 201

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'test1'
            }))
        assert status == 201

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'test2'
            }))
        assert status == 201

        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'group1',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'AllowSingle'
                }]
            }))

        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'group2',
                    'permission': 'guillotina.AccessContent',
                    'setting': 'Allow'
                }, {
                    'principal': 'group1',
                    'permission': 'guillotina.ViewContent',
                    'setting': 'AllowSingle'
                }]
            }))

        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/test1/@sharing',
            data=json.dumps({
                'prinperm': [{
                    'principal': 'group3',
                    'permission': 'guillotina.ViewContent',
                    'setting': 'Allow'
                }]
            }))

        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/testing/test2/@sharing',
            data=json.dumps({
                'prinrole': [{
                    'principal': 'group2',
                    'role': 'guillotina.Reader',
                    'setting': 'Allow'
                }],
                'roleperm': [{
                    'role': 'guillotina.Reader',
                    'permission': 'guillotina.ViewContent',
                    'setting': 'Allow'
                }]
            }))

        assert status == 200

        request = utils.get_mocked_request(requester.db)
        container = await utils.get_container(requester, request)
        content = await container.async_get('testing')

        user = GuillotinaUser(request)
        user.id = 'user1'
        user._groups = ['group2', 'group1']

        utils.login(request, user)

        assert request.security.check_permission('guillotina.AccessContent',
                                                 request.container)
        assert request.security.check_permission('guillotina.AccessContent',
                                                 content)

        user = GuillotinaUser(request)
        user.id = 'user2'
        user._groups = ['group1']

        utils.login(request, user)

        assert request.security.check_permission('guillotina.AccessContent',
                                                 request.container)
        assert not request.security.check_permission(
            'guillotina.AccessContent', content)

        user = GuillotinaUser(request)
        user.id = 'user3'
        user._groups = ['group1', 'group2', 'group3']

        utils.login(request, user)
        test1 = await content.async_get('test1')
        test2 = await content.async_get('test2')

        assert request.security.check_permission(
            'guillotina.ViewContent', test1)
        assert request.security.check_permission(
            'guillotina.ViewContent', test2)
