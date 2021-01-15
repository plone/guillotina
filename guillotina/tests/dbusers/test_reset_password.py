from . import settings
from guillotina.component import get_utility
from guillotina.interfaces import IMailer

import base64
import json
import pytest


pytestmark = pytest.mark.asyncio

NEW_PASSWORD = "password2"


@pytest.mark.app_settings(settings.DEFAULT_REGISTRATION_SETTINGS)
@pytest.mark.parametrize("install_addons", [["dbusers", "email_validation"]])
async def test_reset_password(container_install_requester):
    async with container_install_requester as requester:
        # Add a user first
        resp, status_code = await requester(
            "POST", "/db/guillotina/users", data=json.dumps(settings.user_data)
        )
        assert status_code == 201

        resp, status_code = await requester(
            "POST", "/db/guillotina/@users/foobar/reset-password", authenticated=False
        )
        assert status_code == 200

        util = get_utility(IMailer)
        assert "http://localhost:4200/@@validation" in util.mail[0]["html"]
        assert "<p>Reset password</p>" in util.mail[0]["html"]
        assert "<p>Reset password</p>" in util.mail[0]["html"]
        assert "MYTIMEFORMAT" in util.mail[0]["html"]

        token = (
            util.mail[0]["html"]
            .split("http://localhost:4200/@@validation?token=")[1]
            .split('" target="_blank"')[0]
        )

        resp, status_code = await requester(
            "POST", f"/db/guillotina/@validate_schema/{token}", authenticated=False
        )
        assert status_code == 200
        assert resp["title"] == "Reset password validation information"
        assert resp["properties"]["password"]["minLength"] == 6

        resp, status_code = await requester(
            "POST",
            f"/db/guillotina/@validate/{token}",
            authenticated=False,
            data=json.dumps({"passworda": NEW_PASSWORD}),
        )
        assert status_code == 412

        resp, status_code = await requester(
            "POST",
            f"/db/guillotina/@validate/{token}",
            authenticated=False,
            data=json.dumps({"password": NEW_PASSWORD}),
        )
        assert status_code == 200

        resp, status_code = await requester(
            "POST",
            "/db/guillotina/@login",
            authenticated=False,
            data=json.dumps({"username": "foobar", "password": NEW_PASSWORD}),
        )
        assert status_code == 200


@pytest.mark.app_settings(settings.DEFAULT_REGISTRATION_SETTINGS)
@pytest.mark.parametrize("install_addons", [["dbusers"]])
async def test_change_password(container_install_requester):
    async with container_install_requester as requester:
        # Add a user first
        resp, status_code = await requester(
            "POST", "/db/guillotina/users", data=json.dumps(settings.user_data)
        )
        assert status_code == 201

        resp, status_code = await requester(
            "POST",
            "/db/guillotina/@users/foobar/reset-password",
            token=base64.b64encode(b"foobar:password").decode("utf-8"),
            data=json.dumps({"old_password": "BAD", "new_password": NEW_PASSWORD}),
        )
        assert status_code == 401

        resp, status_code = await requester(
            "POST", "/db/guillotina/@login", data=json.dumps({"username": "foobar", "password": "password"}),
        )
        assert status_code == 200
        token = resp["token"]

        resp, status_code = await requester(
            "POST", "/db/guillotina/groups", data=json.dumps(settings.group_data)
        )
        assert status_code == 201

        resp, status_code = await requester(
            "PATCH",
            "/db/guillotina/users/foobar",
            data=json.dumps({"user_groups": ["foobar_group"], "user_roles": []}),
        )
        assert status_code == 204

        resp, status_code = await requester(
            "POST",
            "/db/guillotina/@users/foobar/reset-password",
            token=base64.b64encode(b"foobar:password").decode("utf-8"),
            data=json.dumps({"old_password": "password", "new_password": NEW_PASSWORD}),
        )
        assert status_code == 200

        resp, status_code = await requester(
            "POST",
            "/db/guillotina/@users/foobar/reset-password",
            token=base64.b64encode(b"foobar:password").decode("utf-8"),
            data=json.dumps({"old_password": "password", "new_password": NEW_PASSWORD}),
        )
        assert status_code == 200

        resp, status_code = await requester(
            "GET", "/db/guillotina/users/foobar", token=token, auth_type="Bearer"
        )
        assert status_code == 200

        resp, status_code = await requester(
            "POST",
            "/db/guillotina/@login",
            authenticated=False,
            data=json.dumps({"username": "foobar", "password": NEW_PASSWORD}),
        )
        assert status_code == 200
