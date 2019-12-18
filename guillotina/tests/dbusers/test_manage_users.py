from . import settings
from guillotina.tests.test_catalog import NOT_POSTGRES

import copy
import json
import pytest


@pytest.fixture()
async def user_data():
    return settings.user_data


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_endpoints_authorization(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Add a user first
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_get_users(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Check 404 is returned on unexisting user
        resp, status_code = await requester("GET", "/db/guillotina/@users/unexisting")
        assert status_code == 404
        assert resp["reason"] == "User unexisting not found"

        # Check initially there is no users
        resp, status_code = await requester("GET", "/db/guillotina/@users")
        assert status_code == 200
        assert len(resp) == 0

        # Add a user
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201

        # Check it gets listed
        resp, status_code = await requester("GET", "/db/guillotina/@users")
        assert status_code == 200
        assert len(resp) == 1
        assert resp[0]["@name"] == "foobar"
        assert resp[0]["fullname"] == "Foobar"
        assert resp[0]["email"] == "foo@bar.com"
        assert isinstance(resp[0]["roles"], list)

        # Check individual get works aswell
        resp, status_code = await requester("GET", "/db/guillotina/@users/foobar")
        assert status_code == 200
        assert resp["@name"] == "foobar"


settings_with_catalog = copy.deepcopy(settings.DEFAULT_SETTINGS)
settings_with_catalog["applications"].append("guillotina.contrib.catalog.pg")
settings_with_catalog.setdefault("load_utilities", {})  # type: ignore
settings_with_catalog["load_utilities"]["catalog"] = {  # type: ignore
    "provides": "guillotina.interfaces.ICatalogUtility",
    "factory": "guillotina.contrib.catalog.pg.PGSearchUtility",
}


@pytest.mark.app_settings(settings_with_catalog)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_list_users_works_with_catalog(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Check initially there is no users
        resp, status_code = await requester("GET", "/db/guillotina/@users")
        assert status_code == 200
        assert len(resp) == 0

        # Add a user
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201

        # Check it gets listed
        resp, status_code = await requester("GET", "/db/guillotina/@users")
        assert status_code == 200
        assert len(resp) == 1
        assert resp[0]["@name"] == "foobar"
        assert resp[0]["fullname"] == "Foobar"
        assert resp[0]["email"] == "foo@bar.com"
        assert isinstance(resp[0]["roles"], list)


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_patch_user_data(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Check 404 is returned
        resp, status_code = await requester("PATCH", "/db/guillotina/@users/unexisting")
        assert status_code == 404
        assert resp["reason"] == "User unexisting not found"

        # Create a user
        _, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201

        # Modify some data
        data = {"email": "foobar2@foo.com", "roles": {"guillotina.Manager": True}}
        _, status_code = await requester("PATCH", "/db/guillotina/@users/foobar", data=json.dumps(data))
        assert status_code == 204

        # Get it now and check it was updated
        resp, status_code = await requester("GET", "/db/guillotina/@users/foobar")
        assert status_code == 200
        assert resp["email"] == "foobar2@foo.com"
        assert "guillotina.Manager" in resp["roles"]


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_delete_user(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Check 404 is returned on nonexisting users
        resp, status_code = await requester("DELETE", "/db/guillotina/@users/unexisting")
        assert status_code == 404
        assert resp["reason"] == "User unexisting not found"

        # Create a user
        _, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201

        # Delete it now
        _, status_code = await requester("DELETE", "/db/guillotina/@users/foobar")
        assert status_code == 200

        # Check user is not there anymore
        _, status_code = await requester("GET", "/db/guillotina/@users/foobar")
        assert status_code == 404
