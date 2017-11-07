from datetime import datetime
from datetime import timedelta
from guillotina._settings import app_settings

import jwt


async def test_jwt_auth(container_requester):
    async with container_requester as requester:
        from guillotina.auth.users import ROOT_USER_ID
        jwt_token = jwt.encode({
            'exp': datetime.utcnow() + timedelta(seconds=60),
            'id': ROOT_USER_ID
        }, app_settings['jwt']['secret']).decode('utf-8')

        response, status = await requester(
            'GET', '/db/guillotina/@addons',
            token=jwt_token,
            auth_type='Bearer'
        )
        assert status == 200
