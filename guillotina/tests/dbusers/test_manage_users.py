from . import settings
import json
import pytest


@pytest.fixture()
async def user_data():
    return settings.user_data


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_get_users(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        resp, status_code = await requester("GET", "/db/guillotina/users")
        resp, status_code = await requester(
            "POST", "/db/guillotina/users", data=json.dumps(user_data)
        )
        assert status_code == 201
        resp, status_code = await requester("GET", "/db/guillotina/@users")
        assert status_code == 200
        assert len(resp) == 1
        assert resp[0]["@name"] == "foobar"
        assert resp[0]["fullname"] == "Foobar"
        assert resp[0]["email"] == "foo@bar.com"
        resp, status_code = await requester("GET", "/db/guillotina/@users/foobar")
        assert status_code == 200
        assert resp["@name"] == "foobar"


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_ensure_can_update_user_accounts(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        resp, status_code = await requester("GET", "/db/guillotina/users")
        resp, status_code = await requester(
            "POST", "/db/guillotina/users", data=json.dumps(user_data)
        )
        assert status_code == 201
        data = {"email": "foobar2@foo.com", "roles": {"guillotina.Manager": True}}
        resp, status_code = await requester(
            "PATCH", "/db/guillotina/@users/foobar", data=json.dumps(data)
        )
        assert status_code == 204
        resp, status_code = await requester(
            "GET", "/db/guillotina/@users/foobar"
        )
        assert status_code == 200
        assert resp["email"] == "foobar2@foo.com"
        assert "guillotina.Manager" in resp["roles"]

        resp, status_code = await requester(
            "DELETE", "/db/guillotina/@users/foobar"
        )
        assert status_code == 200
        resp, status_code = await requester("GET", "/db/guillotina/@users")
        assert status_code == 200
        assert len(resp) == 0
