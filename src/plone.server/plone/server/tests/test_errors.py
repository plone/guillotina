# -*- coding: utf-8 -*-
from plone.server.testing import PloneFunctionalTestCase

import json


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_non_existing_site(self):
        resp = self.layer.requester('GET', '/plone/non')
        self.assertTrue(resp.status_code == 404)

    def test_non_existing_registry(self):
        resp = self.layer.requester('GET', '/plone/plone/@registry/non')
        self.assertTrue(resp.status_code == 404)

    def test_non_existing_type(self):
        resp = self.layer.requester('GET', '/plone/plone/@types/non')
        self.assertTrue(resp.status_code == 400)
        self.assertTrue(json.loads(resp.text)['error']['type'] == 'ViewError')
