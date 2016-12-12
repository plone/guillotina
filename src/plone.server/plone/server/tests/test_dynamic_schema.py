# -*- coding: utf-8 -*-
from plone.server.behaviors.attachment import IAttachment
from plone.server.testing import PloneFunctionalTestCase
from plone.server.tests import TEST_RESOURCES_DIR
from zope import schema
from zope.interface import Interface

import json
import os


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def _get_site(self):
        """
        sometimes the site does not get updated data from zodb
        this seems to make it
        """
        return self.layer.new_root()['plone']

    def test_set_dynamic_behavior(self):
        """Get the application root."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        self.assertTrue(resp.status_code == 201)

        # We create the behavior
        resp = self.layer.requester(
            'PATCH',
            '/plone/plone/item1/@behaviors',
            data=json.dumps({
                'behavior': 'plone.server.behaviors.attachment.IAttachment'
            })
        )
        self.assertTrue(resp.status_code == 200)

        # We check that the behavior is there
        resp = self.layer.requester(
            'GET',
            '/plone/plone/item1'
        )

        self.assertEqual(
            resp.json()['__behaviors__'],
            ['plone.server.behaviors.attachment.IAttachment'])

        self.assertTrue(
            'plone.server.behaviors.attachment.IAttachment' in
            resp.json())

        # We upload a file
        fi = open(os.path.join(TEST_RESOURCES_DIR, 'plone.png'), 'rb')
        data = fi.read()
        fi.close()
        resp = self.layer.requester(
            'PATCH',
            '/plone/plone/item1/@upload/file',
            data=data,
            headers={
                'X-UPLOAD-FILENAME': 'plone.png'
            }
        )

        self.assertTrue(resp.status_code == 200)

        resp = self.layer.requester(
            'GET',
            '/plone/plone/item1'
        )
        self.assertEqual(
            resp.json()['plone.server.behaviors.attachment.IAttachment']['file']['filename'],  # noqa
            'plone.png')


    def test_create_delete_dynamic_behavior(self):
        """Create and delete a content type."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        self.assertTrue(resp.status_code == 201)

        # We create the behavior
        resp = self.layer.requester(
            'PATCH',
            '/plone/plone/item1/@behaviors',
            data=json.dumps({
                'behavior': 'plone.server.behaviors.attachment.IAttachment'
            })
        )
        self.assertTrue(resp.status_code == 200)

        # We check that the behavior is there
        resp = self.layer.requester(
            'GET',
            '/plone/plone/item1'
        )

        self.assertEqual(
            resp.json()['__behaviors__'],
            ['plone.server.behaviors.attachment.IAttachment'])

        # We delete the behavior
        resp = self.layer.requester(
            'DELETE',
            '/plone/plone/item1/@behaviors',
            data=json.dumps({
                'behavior': 'plone.server.behaviors.attachment.IAttachment'
            })
        )
        self.assertTrue(resp.status_code == 200)

        # We check that the behavior is there
        resp = self.layer.requester(
            'GET',
            '/plone/plone/item1'
        )

        self.assertEqual(
            resp.json()['__behaviors__'],
            [])

        self.assertTrue(
            'plone.server.behaviors.attachment.IAttachment' not in
            resp.json())

    def test_get_behaviors(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        self.assertTrue(resp.status_code == 201)

        resp = self.layer.requester(
            'GET',
            '/plone/plone/item1/@behaviors'
        )

        self.assertTrue(resp.status_code == 200)
        self.assertTrue(
            'plone.server.behaviors.attachment.IAttachment' in resp.json()['available'])  # noqa
        self.assertTrue(
            'plone.server.behaviors.attachment.IAttachment' in resp.json())
