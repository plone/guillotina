from . import settings
from guillotina.component import get_utility
from guillotina.interfaces import IMailer

import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(settings.DEFAULT_REGISTRATION_SETTINGS)
@pytest.mark.parametrize("install_addons", [["dbusers", "email_validation"]])
async def test_registration(container_install_requester):
    async with container_install_requester as requester:
        # Add a user first
        resp, status_code = await requester(
            "POST", "/db/guillotina/@users", authenticated=False, data=json.dumps(settings.user_data)
        )
        assert status_code == 200

        util = get_utility(IMailer)
        assert "http://localhost:4200/@@validation" in util.mail[0]["html"]
        assert "<p>Registering user foobar</p>" in util.mail[0]["html"]

        token = (
            util.mail[0]["html"].split("http://localhost:4200/@@validation?token=")[1].split('" target="_blank"')[0]
        )

        resp, status_code = await requester("POST", f"/db/guillotina/@validate/{token}", authenticated=False)
        assert "token" in resp
        assert status_code == 200

        resp, status_code = await requester(
            "POST",
            "/db/guillotina/@login",
            authenticated=False,
            data=json.dumps({"username": "foobar", "password": "password"}),
        )
        assert status_code == 200

        resp, status_code = await requester(
            "POST", "/db/guillotina/@users", authenticated=False, data=json.dumps(settings.user_data)
        )
        assert status_code == 401
