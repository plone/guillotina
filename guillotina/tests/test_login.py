from guillotina.auth.users import ROOT_USER_ID
from guillotina.testing import TESTING_SETTINGS

import json
import jwt


async def test_login(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@login",
            data=json.dumps(
                {"username": ROOT_USER_ID, "password": TESTING_SETTINGS["root_user"]["password"]}
            ),
        )
        assert status == 200
        assert "token" in response
        payload = jwt.decode(response["token"], TESTING_SETTINGS["jwt"]["secret"], algorithms=["HS256"])
        assert payload["id"] == ROOT_USER_ID


async def test_refresh(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/@login",
            data=json.dumps(
                {"username": ROOT_USER_ID, "password": TESTING_SETTINGS["root_user"]["password"]}
            ),
        )
        assert status == 200

        response, status = await requester("POST", "/db/guillotina/@login-renew")
        assert status == 200
        assert "token" in response
        payload = jwt.decode(response["token"], TESTING_SETTINGS["jwt"]["secret"], algorithms=["HS256"])
        assert payload["id"] == ROOT_USER_ID


async def test_login_root(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/@login",
            data=json.dumps(
                {"username": ROOT_USER_ID, "password": TESTING_SETTINGS["root_user"]["password"]}
            ),
        )
        assert status == 200
        assert "token" in response
        payload = jwt.decode(response["token"], TESTING_SETTINGS["jwt"]["secret"], algorithms=["HS256"])
        assert payload["id"] == ROOT_USER_ID


async def test_refresh_root(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/@login",
            data=json.dumps(
                {"username": ROOT_USER_ID, "password": TESTING_SETTINGS["root_user"]["password"]}
            ),
        )
        assert status == 200

        response, status = await requester("POST", "/@login-renew")
        assert status == 200
        assert "token" in response
        payload = jwt.decode(response["token"], TESTING_SETTINGS["jwt"]["secret"], algorithms=["HS256"])
        assert payload["id"] == ROOT_USER_ID
