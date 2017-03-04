# -*- coding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from guillotina.auth import get_principals_with_access_content
from guillotina.auth import get_roles_with_access_content
from guillotina.browser import View
from guillotina.interfaces import IRequest
from guillotina.testing import GuillotinaFunctionalTestCase
from zope.interface import alsoProvides

import json


class PrincipalsView(View):
    def __call__(self):
        return get_principals_with_access_content(self.context)


class RolesView(View):
    def __call__(self):
        return get_roles_with_access_content(self.context)


class FunctionalTestServer(GuillotinaFunctionalTestCase):
    """Functional testing of the API REST."""

    def _get_site(self):
        """
        sometimes the site does not get updated data from zodb
        this seems to make it
        """
        return self.new_root()['guillotina']

    def test_get_guillotina(self):
        """Get the root guillotina site."""
        resp = self.layer.requester('GET', '/guillotina/guillotina/@sharing')
        response = json.loads(resp.text)
        self.assertTrue(response['local']['prinrole']['root']['guillotina.SiteAdmin'] == 'Allow')
        self.assertTrue(response['local']['prinrole']['root']['guillotina.Owner'] == 'Allow')

    def test_set_local_guillotina(self):
        """Get the root guillotina site."""
        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/@sharing',
            data=json.dumps({
                'type': 'AllowSingle',
                'prinperm': {
                    'user1': [
                        'guillotina.AccessContent'
                    ]
                }
            })
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'testing'
            })
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.layer.requester('GET', '/guillotina/guillotina/testing/@sharing')

        response = json.loads(resp.text)
        self.assertTrue(len(response['inherit']) == 1)
        self.assertTrue(
            response['inherit'][0]['prinrole']['root']['guillotina.SiteAdmin'] == 'Allow')
        self.assertTrue(
            response['inherit'][0]['prinrole']['root']['guillotina.Owner'] == 'Allow')
        self.assertTrue(
            response['inherit'][0]['prinperm']['user1']['guillotina.AccessContent'] == 'AllowSingle')  # noqa

        # Check the access users/roles
        testing_object = self._get_site()['testing']
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        principals = PrincipalsView(testing_object, request)()
        self.assertEqual(principals, ['root'])
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        roles = RolesView(testing_object, request)()
        self.assertEqual(roles, ['guillotina.SiteAdmin'])

        # Now we add the user1 with inherit on the site
        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/@sharing',
            data=json.dumps({
                'type': 'Allow',
                'prinperm': {
                    'user1': [
                        'guillotina.AccessContent'
                    ]
                }
            })
        )
        testing_object = self._get_site()['testing']
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        principals = PrincipalsView(testing_object, request)()
        self.assertEqual(len(principals), 2)
        self.assertTrue('user1' in principals)

        # Now we add the user1 with deny on the object
        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/testing/@sharing',
            data=json.dumps({
                'type': 'Deny',
                'prinperm': {
                    'user1': [
                        'guillotina.AccessContent'
                    ]
                }
            })
        )
        testing_object = self._get_site()['testing']
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        principals = PrincipalsView(testing_object, request)()
        self.assertEqual(principals, ['root'])
