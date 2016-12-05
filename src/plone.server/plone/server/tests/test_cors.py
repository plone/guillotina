# -*- coding: utf-8 -*-
from plone.server.testing import PloneFunctionalTestCase


class FunctionalCorsTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_get_root(self):
        """Get the application root."""
        resp = self.layer.requester('OPTIONS', '/plone/plone', headers={
            'Origin': 'http://localhost',
            'Access-Control-Request-Method': 'Get'
        })
        self.assertTrue('ACCESS-CONTROL-ALLOW-CREDENTIALS' in resp.headers)
        self.assertTrue('ACCESS-CONTROL-EXPOSE-HEADERS' in resp.headers)
        self.assertTrue('ACCESS-CONTROL-ALLOW-HEADERS' in resp.headers)
