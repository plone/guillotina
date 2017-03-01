# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
from guillotina import app_settings
from guillotina.testing import GuillotinaFunctionalTestCase

import jwt


class TestAuth(GuillotinaFunctionalTestCase):

    def test_jwt_auth(self):
        from guillotina.auth.users import ROOT_USER_ID
        jwt_token = jwt.encode({
            'exp': datetime.utcnow() + timedelta(seconds=60),
            'id': ROOT_USER_ID
        }, app_settings['jwt']['secret']).decode('utf-8')

        resp = self.layer.requester(
            'GET', '/guillotina/guillotina/@addons',
            token=jwt_token,
            auth_type='Bearer'
        )
        assert resp.status_code == 200
