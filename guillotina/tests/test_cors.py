# -*- coding: utf-8 -*-
from guillotina.testing import GuillotinaFunctionalTestCase


class FunctionalCorsTestServer(GuillotinaFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_get_root(self):
        """Get the application root."""
        resp = self.layer.requester('OPTIONS', '/guillotina/guillotina', headers={
            'Origin': 'http://localhost',
            'Access-Control-Request-Method': 'Get'
        })
        self.assertTrue('ACCESS-CONTROL-ALLOW-CREDENTIALS' in resp.headers)
        self.assertTrue('ACCESS-CONTROL-EXPOSE-HEADERS' in resp.headers)
        self.assertTrue('ACCESS-CONTROL-ALLOW-HEADERS' in resp.headers)
