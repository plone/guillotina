# -*- coding: utf-8 -*-
from plone.server.testing import PloneFunctionalTestCase

import json


class FunctionalTestServer(PloneFunctionalTestCase):

    def test_get_root(self):
        resp = self.layer.requester('GET', '/')
        response = json.loads(resp.text)
        self.assertEqual(response['static_file'], ['favicon.ico'])
        self.assertEqual(response['databases'], ['plone'])
        self.assertTrue('country-flags' in response['static_directory'])
        self.assertTrue('language-flags' in response['static_directory'])

    def test_get_database(self):
        resp = self.layer.requester('GET', '/plone')
        response = json.loads(resp.text)
        self.assertTrue(len(response['sites']) == 0)
