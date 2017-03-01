# -*- coding: utf-8 -*-
from guillotina.testing import GuillotinaFunctionalTestCase

import json


class FunctionalTestServer(GuillotinaFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_non_existing_site(self):
        resp = self.layer.requester('GET', '/guillotina/non')
        self.assertTrue(resp.status_code == 404)

    def test_non_existing_registry(self):
        resp = self.layer.requester('GET', '/guillotina/guillotina/@registry/non')
        self.assertTrue(resp.status_code == 404)

    def test_non_existing_type(self):
        resp = self.layer.requester('GET', '/guillotina/guillotina/@types/non')
        self.assertTrue(resp.status_code == 400)
        self.assertTrue(json.loads(resp.text)['error']['type'] == 'ViewError')
