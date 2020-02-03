import pytest
import json
import jwt
from . import settings
from guillotina.auth.users import ROOT_USER_ID
from guillotina.testing import TESTING_SETTINGS

pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_login_root_session(redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/@login",
            authenticated=False,
            data=json.dumps(
                {"username": ROOT_USER_ID, "password": TESTING_SETTINGS["root_user"]["password"]}
            ),
        )
        assert status == 200
        assert "token" in response
        payload = jwt.decode(response["token"], TESTING_SETTINGS["jwt"]["secret"], algorithms=["HS256"])
        assert "session" in payload

        valid_token = response["token"]

        response, status = await requester(
            "GET",
            "/@users/root/sessions",
            auth_type="Bearer",
            token=valid_token
        )
        assert status == 200
        assert len(response) == 1

        response, status = await requester(
            "GET",
            f"/@users/root/session/{response[0]}",
            auth_type="Bearer",
            token=valid_token
        )

        assert status == 200
        assert response['user-agent'] == 'ASGI-Test-Client'


        response, status = await requester(
            "POST",
            "/@login-renew",
            auth_type="Bearer",
            token=valid_token
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/@logout",
            auth_type="Bearer",
            token=valid_token
        )
        assert status == 200
        
        response, status = await requester(
            "GET",
            f"/@users/root/sessions",
            auth_type="Bearer",
            token=valid_token
        )

        assert status == 401
