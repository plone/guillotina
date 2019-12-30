from . import settings
from guillotina.tests.utils import get_container

import base64
import json
import pytest
import random


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
            "GET", "/db/guillotina/users/foobar", token=resp["token"], auth_type="Bearer"
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


async def create_user(requester, user_id, user_data=None):
    user_data = user_data or {}
    user_data["id"] = user_id
    data = {"@type": "User"}
    data.update(user_data)
    _, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(data))
    assert status_code == 201


async def login_user(requester, username, password):
    resp, status_code = await requester(
        "POST", "/db/guillotina/@login", data=json.dumps({"username": username, "password": password})
    )
    assert status_code == 200
    return resp["token"]


async def create_and_login_user(requester, user_id, password, roles):
    await create_user(requester, user_id, user_data={"password": password, "user_roles": roles})
    return await login_user(requester, user_id, password)


async def _test_endpoint_access(requester, method, url, data=None, allowed_roles=None):  # pragma: no cover
    data = data or {}
    allowed_roles = allowed_roles or []
    all_roles = [
        "guillotina.Manager",
        "guillotina.ContainerAdmin",
        "guillotina.Member",
        "guillotina.ContainerCreator",
        "guillotina.ContainerDeleter",
    ]

    for role in all_roles:
        # Get a random user id
        uid = f"user-{random.randint(0, 9999)}"

        token = await create_and_login_user(requester, uid, "password", roles=[role])

        # Try creating a user now
        _, status_code = await requester(method, url, data=json.dumps(data), auth_type="Bearer", token=token)

        if role in allowed_roles:
            assert status_code != 401
        else:
            assert status_code == 401


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_only_root_and_admins_can_create_users(dbusers_requester):
    async with dbusers_requester as requester:
        await _test_endpoint_access(
            requester,
            "POST",
            "/db/guillotina/users",
            allowed_roles=["guillotina.Manager", "guillotina.ContainerAdmin"],
        )


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_only_root_and_admins_can_manage_users_and_groups(dbusers_requester):
    async with dbusers_requester as requester:
        for method, url in [
            ("GET", "@users"),
            ("GET", "@users/foo"),
            ("PATCH", "@users/foo"),
            ("DELETE", "@users/foo"),
            ("GET", "@groups"),
            ("GET", "@groups/foo"),
            ("PATCH", "@groups/foo"),
            ("DELETE", "@groups/foo"),
        ]:
            await _test_endpoint_access(
                requester,
                method,
                "/db/guillotina/" + url,
                allowed_roles=["guillotina.Manager", "guillotina.ContainerAdmin"],
            )
