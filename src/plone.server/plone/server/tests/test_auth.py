# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
from plone.server import app_settings
from plone.server.testing import PloneFunctionalTestCase

import jwt


class TestAuth(PloneFunctionalTestCase):

    def test_jwt_auth(self):
        from plone.server.auth.participation import ROOT_USER_ID
        jwt_token = jwt.encode({
            'exp': datetime.utcnow() + timedelta(seconds=60),
            'id': ROOT_USER_ID
        }, app_settings['jwt']['secret']).decode('utf-8')

        resp = self.layer.requester(
            'GET', '/plone/plone/@addons',
            token=jwt_token
        )
        assert resp.status_code == 200
