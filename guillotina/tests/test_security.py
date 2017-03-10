# -*- coding: utf-8 -*-
from guillotina.security.utils import get_principals_with_access_content
from guillotina.security.utils import get_roles_with_access_content
from guillotina.tests import utils

import json


async def test_get_guillotina(site_requester):
    async with await site_requester as requester:
        response, status = await requester('GET', '/db/guillotina/@sharing')
        assert response['local']['prinrole']['root']['guillotina.SiteAdmin'] == 'Allow'
        assert response['local']['prinrole']['root']['guillotina.Owner'] == 'Allow'


async def test_database_root_has_none_parent(site_requester):
    async with await site_requester as requester:
        # important for security checks to not inherit...
        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        assert root.__parent__ is None


async def test_set_local_guillotina(site_requester):
    async with await site_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'type': 'AllowSingle',
                'prinperm': {
                    'user1': [
                        'guillotina.AccessContent'
                    ]
                }
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
        assert response['inherit'][0]['prinrole']['root']['guillotina.SiteAdmin'] == 'Allow'
        assert response['inherit'][0]['prinrole']['root']['guillotina.Owner'] == 'Allow'
        assert 'Anonymous User' not in response['inherit'][0]['prinrole']
        assert response['inherit'][0]['prinperm']['user1']['guillotina.AccessContent'] == 'AllowSingle'  # noqa

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        site = await root.async_get('guillotina')
        testing_object = await site.async_get('testing')

        # Check the access users/roles
        principals = get_principals_with_access_content(testing_object, request)
        assert principals == ['root']
        roles = get_roles_with_access_content(testing_object, request)
        assert roles == ['guillotina.SiteAdmin']

        # Now we add the user1 with inherit on the site
        response, status = await requester(
            'POST',
            '/db/guillotina/@sharing',
            data=json.dumps({
                'type': 'Allow',
                'prinperm': {
                    'user1': [
                        'guillotina.AccessContent'
                    ]
                }
            })
        )

        # need to retreive objs again from db since they changed
        site = await root.async_get('guillotina')
        testing_object = await site.async_get('testing')
        principals = get_principals_with_access_content(testing_object, request)
        assert len(principals) == 2
        assert 'user1' in principals

        # Now we add the user1 with deny on the object
        response, status = await requester(
            'POST',
            '/db/guillotina/testing/@sharing',
            data=json.dumps({
                'type': 'Deny',
                'prinperm': {
                    'user1': [
                        'guillotina.AccessContent'
                    ]
                }
            })
        )
        # need to retreive objs again from db since they changed
        site = await root.async_get('guillotina')
        testing_object = await site.async_get('testing')
        principals = get_principals_with_access_content(testing_object, request)
        assert principals == ['root']
