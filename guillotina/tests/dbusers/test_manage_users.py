from . import settings
from guillotina.tests.test_catalog import NOT_POSTGRES

import copy
import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def user_data():
    return settings.user_data.copy()


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

        _, status_code = await requester("GET", "/db/guillotina/@users/foobar")
        assert status_code == 404

        # Create a user
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201

        resp, status = await requester("GET", "/db/guillotina/@users/foobar")

        # Modify some data
        data = {"email": "foobar2@foo.com", "roles": {"guillotina.Manager": True}}
        resp, status_code = await requester("PATCH", "/db/guillotina/@users/foobar", data=json.dumps(data))
        assert status_code == 204

        # Get it now and check it was updated
        resp, status_code = await requester("GET", "/db/guillotina/@users/foobar")
        assert status_code == 200
        assert resp["email"] == "foobar2@foo.com"
        assert "guillotina.Manager" in resp["roles"]


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_patch_groups_on_user_updates_groups(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Create a user
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        assert status_code == 201
        # create groups
        group = {"name": "foo", "@type": "Group", "id": "foo"}
        _, status = await requester("POST", "/db/guillotina/groups/", data=json.dumps(group))
        assert status == 201
        group2 = {"name": "foo2", "@type": "Group", "id": "foo2"}
        _, status = await requester("POST", "/db/guillotina/groups/", data=json.dumps(group2))
        assert status == 201

        async def update_groups(lg):
            return await requester(
                "PATCH", "/db/guillotina/users/foobar", data=json.dumps({"user_groups": lg})
            )

        async def check_users_group(gr):
            resp, _ = await requester("GET", f"/db/guillotina/@groups/{gr}")
            return resp["users"]["items"]

        await update_groups(["foo"])
        assert "foobar" in await check_users_group("foo")
        await update_groups(["foo", "foo2"])
        assert "foobar" in await check_users_group("foo")
        assert "foobar" in await check_users_group("foo2")
        await update_groups(["foo2"])

        assert "foobar" not in await check_users_group("foo")
        assert "foobar" in await check_users_group("foo2")
        await update_groups([])
        assert len(await check_users_group("foo2")) == 0

        # delete a group
        await update_groups(["foo", "foo2"])
        await requester("DELETE", "/db/guillotina/groups/foo")
        # ensure user id updated
        result, _ = await requester("GET", "/db/guillotina/users/foobar")
        assert result["user_groups"] == ["foo2"]
        # remove a user
        await requester("DELETE", "/db/guillotina/users/foobar")
        result, _ = await requester("GET", "/db/guillotina/groups/foo2")
        assert len(result["users"]) == 0


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


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_get_available_roles(dbusers_requester):
    async with dbusers_requester as requester:
        resp, status_code = await requester("GET", "/db/guillotina/@available-roles")
        assert "guillotina.Anonymous" in resp
        assert "guillotina.Manager" in resp


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_users_cannot_be_added_outside_users_folder(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Add a outside users folder
        resp, status_code = await requester("POST", "/db/guillotina", data=json.dumps(user_data))
        assert status_code == 412
        assert resp["reason"] == "notAllowed"
        assert resp["details"] == "Type not allowed to be added here"
