from . import settings
from guillotina.tests.utils import get_container

import base64
import json
import pytest


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_add_user(dbusers_requester):
    async with dbusers_requester as requester:
        # Create a user
        _, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(settings.user_data))
        assert status_code == 201

        # Check user is created in the apropriate folder
        container = await get_container(requester=requester)
        users = await container.async_get("users")
        assert await users.async_contains("foobar")


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_user_auth(dbusers_requester):
    async with dbusers_requester as requester:
        await requester("POST", "/db/guillotina/users", data=json.dumps(settings.user_data))

        # user should be able to add content to object
        resp, status_code = await requester(
            "POST",
            "/db/guillotina/users/foobar",
            data=json.dumps({"@type": "Item", "id": "foobaritem", "title": "foobar"}),
            token=base64.b64encode(b"foobar:password").decode("ascii"),
            auth_type="Basic",
        )
        container = await get_container(requester=requester)
        users = await container.async_get("users")
        foobar = await users.async_get("foobar")
        assert await foobar.async_contains("foobaritem")


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_login(dbusers_requester):
    async with dbusers_requester as requester:
        await requester("POST", "/db/guillotina/users", data=json.dumps(settings.user_data))

        # Login as new user
        resp, status_code = await requester(
            "POST", "/db/guillotina/@login", data=json.dumps({"username": "foobar", "password": "password"})
        )
        assert status_code == 200

        # User should have access to its own folder
        _, status_code = await requester(
            "GET", "/db/guillotina/@users/foobar", token=resp["token"], auth_type="Bearer"
        )
        assert status_code == 200


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_refresh(dbusers_requester):
    async with dbusers_requester as requester:
        # Create a user
        _, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(settings.user_data))
        assert status_code == 201

        # Login
        resp, status_code = await requester(
            "POST", "/db/guillotina/@login", data=json.dumps({"username": "foobar", "password": "password"})
        )
        assert status_code == 200

        # Attempt renew
        resp, status_code = await requester(
            "POST", "/db/guillotina/@login-renew", token=resp["token"], auth_type="Bearer"
        )
        assert status_code == 200
        assert "token" in resp
