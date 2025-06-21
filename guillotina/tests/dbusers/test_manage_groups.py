from . import settings
from guillotina.tests.test_catalog import NOT_POSTGRES

import copy
import json
import pytest


pytestmark = pytest.mark.asyncio


_group = {
    "name": "foo",
    "description": "foo description",
    "@type": "Group",
    "id": "foo",
}


@pytest.fixture()
async def user_data():
    return settings.user_data.copy()


@pytest.fixture()
async def second_user_data():
    return settings.second_user_data.copy()


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_ensure_crud_groups(dbusers_requester, user_data, second_user_data):
    async with dbusers_requester as requester:
        resp, status_code = await requester("POST", "/db/guillotina/groups", data=json.dumps(_group))
        assert status_code == 201
        resp, status_code = await requester("GET", "/db/guillotina/@groups")
        assert status_code == 200
        assert len(resp) == 1
        assert resp[0]["groupname"] == "foo"

        data = {
            "roles": {
                "guillotina.Manager": True,
                "guillotina.Tester": True,
                "guillotina.Bad": False,
            }
        }

        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/@groups/foo")
        assert set(resp["roles"]) == set(["guillotina.Manager", "guillotina.Tester"])

        data = {"roles": {"guillotina.Manager": False}}
        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/@groups/foo")
        assert set(resp["roles"]) == set(["guillotina.Tester"])

        # create the user
        resp, status_code = await requester("GET", "/db/guillotina/users")
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(second_user_data))

        data = {"users": {"foobar": True}}
        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/@groups/foo")
        assert set(resp["users"]["items"]) == set(["foobar"])

        # fix bug https://github.com/plone/guillotina/issues/1069
        resp, status = await requester(
            "PATCH",
            "/db/guillotina/@groups/foo",
            data=json.dumps({"user_roles": ["guillotina.Reader"]}),
        )
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/@groups/foo")
        assert set(resp["users"]["items"]) == set(["foobar"])

        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == ["foo"]

        data = {"users": {"foobar": True}}
        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 204

        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == ["foo"]

        data = {"users": {"foobar": False, "foobar_2": True}}
        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/@groups/foo")
        assert len(resp["users"]["items"]) == 1
        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == []
        resp, status = await requester("GET", "/db/guillotina/users/foobar_2")
        assert resp["user_groups"] == ["foo"]

        data = {"users": {"foobar": False, "foobar_2": False}}
        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/@groups/foo")
        assert len(resp["users"]["items"]) == 0
        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == []
        resp, status = await requester("GET", "/db/guillotina/users/foobar_2")
        assert resp["user_groups"] == []

        # ensure we cannot patch invalid users
        data = {"users": {"foobarx": True}}
        resp, status = await requester("PATCH", "/db/guillotina/@groups/foo", data=json.dumps(data))
        assert status == 412


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_ensure_crud_groups_using_standard_api(dbusers_requester, user_data, second_user_data):
    async with dbusers_requester as requester:
        resp, status_code = await requester("POST", "/db/guillotina/groups", data=json.dumps(_group))
        assert status_code == 201

        data = {"user_roles": ["guillotina.Manager", "guillotina.Tester"]}

        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/groups/foo")
        assert set(resp["user_roles"]) == set(["guillotina.Manager", "guillotina.Tester"])

        data = {"user_roles": ["guillotina.Tester"]}
        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/groups/foo")
        assert set(resp["user_roles"]) == set(["guillotina.Tester"])

        # create the user
        resp, status_code = await requester("GET", "/db/guillotina/users")
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(user_data))
        resp, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(second_user_data))

        data = {"users": ["foobar"]}
        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/groups/foo")
        assert resp["users"] == ["foobar"]

        # fix bug https://github.com/plone/guillotina/issues/1069
        resp, status = await requester(
            "PATCH", "/db/guillotina/groups/foo", data=json.dumps({"user_roles": ["guillotina.Reader"]})
        )
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/groups/foo")
        assert resp["users"] == ["foobar"]

        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == ["foo"]

        data = {"users": ["foobar"]}
        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 204

        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == ["foo"]

        data = {"users": ["foobar_2"]}
        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/groups/foo")
        assert len(resp["users"]) == 1
        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == []
        resp, status = await requester("GET", "/db/guillotina/users/foobar_2")
        assert resp["user_groups"] == ["foo"]

        data = {"users": []}
        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 204
        resp, status = await requester("GET", "/db/guillotina/groups/foo")
        assert len(resp["users"]) == 0
        resp, status = await requester("GET", "/db/guillotina/users/foobar")
        assert resp["user_groups"] == []
        resp, status = await requester("GET", "/db/guillotina/users/foobar_2")
        assert resp["user_groups"] == []

        # ensure we cannot patch invalid users
        data = {"users": {"foobarx": True}}
        resp, status = await requester("PATCH", "/db/guillotina/groups/foo", data=json.dumps(data))
        assert status == 412


settings_with_catalog = copy.deepcopy(settings.DEFAULT_SETTINGS)
settings_with_catalog["applications"].append("guillotina.contrib.catalog.pg")
settings_with_catalog.setdefault("load_utilities", {})  # type: ignore
settings_with_catalog["load_utilities"]["catalog"] = {  # type: ignore
    "provides": "guillotina.interfaces.ICatalogUtility",
    "factory": "guillotina.contrib.catalog.pg.utility.PGSearchUtility",
}


@pytest.mark.app_settings(settings_with_catalog)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_list_groups_works_with_catalog(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Check initially there is no users
        resp, status_code = await requester("GET", "/db/guillotina/@groups")
        assert status_code == 200
        assert len(resp) == 0

        # Add a user
        resp, status_code = await requester("POST", "/db/guillotina/groups", data=json.dumps(_group))
        assert status_code == 201

        # Check it gets listed
        resp, status_code = await requester("GET", "/db/guillotina/@groups")
        assert status_code == 200
        assert len(resp) == 1
        assert resp[0]["@name"]
        assert resp[0]["title"]
        assert isinstance(resp[0]["roles"], list)
        assert isinstance(resp[0]["users"], list)


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_groups_cannot_be_added_outside_groups_folder(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        # Add a outside users folder
        resp, status_code = await requester("POST", "/db/guillotina", data=json.dumps(_group))
        assert status_code == 412
        assert resp["reason"] == "notAllowed"
        assert resp["details"] == "Type not allowed to be added here"


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_create_groups_by_endpoint(dbusers_requester, user_data):
    async with dbusers_requester as requester:
        payload_groups = {
            "groupname": "foo_group",
            "title": "Group",
            "description": "Foo group",
            "roles": ["guillotina.Editor"],
        }
        resp, status = await requester("POST", "/db/guillotina/@groups", data=json.dumps(payload_groups))
        assert status == 200
        resp, status = await requester("GET", f"/db/guillotina/groups/{resp['id']}")
        assert status == 200
