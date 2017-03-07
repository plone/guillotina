# -*- coding: utf-8 -*-
from guillotina.testing import GuillotinaFunctionalTestCase
from guillotina.tests import TEST_RESOURCES_DIR

import json
import os


class FunctionalTestServer(GuillotinaFunctionalTestCase):
    """Functional testing of the API REST."""

    def _get_site(self):
        """
        sometimes the site does not get updated data from zodb
        this seems to make it
        """
        return self.layer.new_root()['guillotina']

    def test_set_dynamic_behavior(self):
        """Get the application root."""
        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/',
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
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        self.assertTrue(resp.status_code == 200)

        # We check that the behavior is there
        resp = self.layer.requester(
            'GET',
            '/guillotina/guillotina/item1'
        )

        self.assertEqual(
            resp.json()['__behaviors__'],
            ['guillotina.behaviors.dublincore.IDublinCore'])

        self.assertTrue(
            'guillotina.behaviors.dublincore.IDublinCore' in
            resp.json())

        # We upload a file
        fi = open(os.path.join(TEST_RESOURCES_DIR, 'plone.png'), 'rb')
        data = fi.read()
        fi.close()
        resp = self.layer.requester(
            'PATCH',
            '/guillotina/guillotina/item1/@upload/file',
            data=data,
            headers={
                'X-UPLOAD-FILENAME': 'plone.png'
            }
        )

        self.assertTrue(resp.status_code == 200)

        resp = self.layer.requester(
            'GET',
            '/guillotina/guillotina/item1'
        )
        self.assertEqual(
            resp.json()['guillotina.behaviors.dublincore.IDublinCore']['file']['filename'],  # noqa
            'plone.png')

    def test_create_delete_dynamic_behavior(self):
        """Create and delete a content type."""
        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/',
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
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        self.assertTrue(resp.status_code == 200)

        # We check that the behavior is there
        resp = self.layer.requester(
            'GET',
            '/guillotina/guillotina/item1'
        )

        self.assertEqual(
            resp.json()['__behaviors__'],
            ['guillotina.behaviors.dublincore.IDublinCore'])

        # We delete the behavior
        resp = self.layer.requester(
            'DELETE',
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        self.assertTrue(resp.status_code == 200)

        # We check that the behavior is there
        resp = self.layer.requester(
            'GET',
            '/guillotina/guillotina/item1'
        )

        self.assertEqual(
            resp.json()['__behaviors__'],
            [])

        self.assertTrue(
            'guillotina.behaviors.dublincore.IDublinCore' not in
            resp.json())

    def test_get_behaviors(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'POST',
            '/guillotina/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        self.assertTrue(resp.status_code == 201)

        resp = self.layer.requester(
            'GET',
            '/guillotina/guillotina/item1/@behaviors'
        )

        self.assertTrue(resp.status_code == 200)
        self.assertTrue(
            'guillotina.behaviors.dublincore.IDublinCore' in resp.json()['available'])  # noqa
        self.assertTrue(
            'guillotina.behaviors.dublincore.IDublinCore' in resp.json())
