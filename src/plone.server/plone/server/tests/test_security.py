# -*- coding: utf-8 -*-
from plone.server.behaviors.attachment import IAttachment
from plone.server.testing import PloneFunctionalTestCase
from plone.server.tests import TEST_RESOURCES_DIR
from zope import schema
from zope.interface import Interface
from plone.server.interfaces import IRequest
from zope.interface import alsoProvides
from plone.server.browser import View
from aiohttp.test_utils import make_mocked_request
from plone.server.auth import get_roles_with_access_content
from plone.server.auth import get_principals_with_access_content

import json
import os


class PrincipalsView(View):
    def __call__(self):
        return get_principals_with_access_content(self.context)


class RolesView(View):
    def __call__(self):
        return get_roles_with_access_content(self.context)


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def _get_site(self):
        """
        sometimes the site does not get updated data from zodb
        this seems to make it
        """
        return self.layer.new_root()['plone']

    def test_get_plone(self):
        """Get the root plone site."""
        resp = self.layer.requester('GET', '/plone/plone/@sharing')
        response = json.loads(resp.text)
        self.assertTrue(response['local']['prinrole']['root']['plone.SiteAdmin'] == 'Allow')
        self.assertTrue(response['local']['prinrole']['root']['plone.Owner'] == 'Allow')

    def test_set_local_plone(self):
        """Get the root plone site."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/@sharing',
            data=json.dumps({
                'type': 'AllowSingle',
                'prinperm': {
                    'user1': [
                        'plone.AccessContent'
                    ]
                }
            })
        )
        self.assertEqual(resp.status_code, 200)

        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                '@type': 'Item',
                'id': 'testing'
            })
        )
        self.assertEqual(resp.status_code, 201)

        resp = self.layer.requester('GET', '/plone/plone/testing/@sharing')

        response = json.loads(resp.text)
        self.assertTrue(len(response['inherit']) == 1)
        self.assertTrue(response['inherit'][0]['prinrole']['root']['plone.SiteAdmin'] == 'Allow')
        self.assertTrue(response['inherit'][0]['prinrole']['root']['plone.Owner'] == 'Allow')
        self.assertTrue(response['inherit'][0]['prinperm']['user1']['plone.AccessContent'] == 'AllowSingle')

        # Check the access users/roles
        testing_object = self._get_site()['testing']
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        principals = PrincipalsView(testing_object, request)()
        self.assertEqual(principals, ['root'])
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        roles = RolesView(testing_object, request)()
        self.assertEqual(roles, ['plone.SiteAdmin'])

        # Now we add the user1 with inherit on the site
        resp = self.layer.requester(
            'POST',
            '/plone/plone/@sharing',
            data=json.dumps({
                'type': 'Allow',
                'prinperm': {
                    'user1': [
                        'plone.AccessContent'
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
            '/plone/plone/testing/@sharing',
            data=json.dumps({
                'type': 'Deny',
                'prinperm': {
                    'user1': [
                        'plone.AccessContent'
                    ]
                }
            })
        )
        testing_object = self._get_site()['testing']
        request = make_mocked_request('POST', '/')
        alsoProvides(request, IRequest)
        principals = PrincipalsView(testing_object, request)()
        self.assertEqual(principals, ['root'])