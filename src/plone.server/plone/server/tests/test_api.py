# -*- coding: utf-8 -*-
from plone.server.testing import PloneFunctionalTestCase

import json


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_get_root(self):
        """Get the application root."""
        resp = self.layer.requester('GET', '/')
        response = json.loads(resp.text)
        self.assertEqual(response['static_file'], ['favicon.ico'])
        self.assertEqual(response['databases'], ['plone'])
        self.assertTrue('country-flags' in response['static_directory'])
        self.assertTrue('language-flags' in response['static_directory'])

    def test_get_database(self):
        """Get the database object."""
        resp = self.layer.requester('GET', '/plone')
        response = json.loads(resp.text)
        self.assertTrue(len(response['sites']) == 1)

    def test_get_plone(self):
        """Get the root plone site."""
        resp = self.layer.requester('GET', '/plone/plone')
        response = json.loads(resp.text)
        self.assertTrue(len(response['member']) == 0)

    def test_get_contenttypes(self):
        """Check list of content types."""
        resp = self.layer.requester('GET', '/plone/plone/@types')
        self.assertTrue(resp.status_code == 200)
        response = json.loads(resp.text)
        self.assertTrue(len(response) > 1)
        self.assertTrue(any("Item" in s['title'] for s in response))
        self.assertTrue(any("Plone Site" in s['title'] for s in response))

    def test_get_contenttype(self):
        """Get a content type definition."""
        resp = self.layer.requester('GET', '/plone/plone/@types/Item')
        self.assertTrue(resp.status_code == 200)
        response = json.loads(resp.text)
        self.assertTrue(len(response[0]['properties']), 5)
        self.assertTrue(response[0]['title'] == 'Item')

    def test_get_registries(self):
        """Get the list of registries."""
        resp = self.layer.requester('GET', '/plone/plone/@registry')
        self.assertTrue(resp.status_code == 200)
        response = json.loads(resp.text)
        self.assertTrue(len(response) >= 10)
        self.assertTrue(
            'plone.server.registry.ILayers.active_layers' in response)

    def test_get_registry(self):
        """Check a value from registry."""
        resp = self.layer.requester(
            'GET',
            '/plone/plone/@registry/plone.server.registry.ICors.enabled')
        response = json.loads(resp.text)
        self.assertTrue(response[0])

    def test_create_contenttype(self):
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

    def test_create_delete_contenttype(self):
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
        resp = self.layer.requester('DELETE', '/plone/plone/item1')
        self.assertTrue(resp.status_code == 200)

    def test_register_registry(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/@registry',
            data=json.dumps({
                "interface": "plone.server.registry.ICors"
            })
        )
        self.assertTrue(resp.status_code == 201)

    def test_update_registry(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'PATCH',
            '/plone/plone/@registry/plone.server.registry.ICors.enabled',
            data=json.dumps({
                "value": False
            })
        )
        self.assertTrue(resp.status_code == 204)
        resp = self.layer.requester(
            'GET',
            '/plone/plone/@registry/plone.server.registry.ICors.enabled')
        response = json.loads(resp.text)
        self.assertFalse(response[0])