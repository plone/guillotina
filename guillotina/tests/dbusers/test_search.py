from . import settings

import copy
import json
import os
import pytest


pytestmark = pytest.mark.asyncio

NOT_POSTGRES = os.environ.get("DATABASE", "DUMMY") in ("cockroachdb", "DUMMY")
PG_CATALOG_SETTINGS = copy.deepcopy(settings.DEFAULT_SETTINGS)
PG_CATALOG_SETTINGS["applications"].append("guillotina.contrib.catalog.pg")
PG_CATALOG_SETTINGS.setdefault("load_utilities", {})  # type: ignore
PG_CATALOG_SETTINGS["load_utilities"]["catalog"] = {  # type: ignore
    "provides": "guillotina.interfaces.ICatalogUtility",
    "factory": "guillotina.contrib.catalog.pg.utility.PGSearchUtility",
}


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_search_user(dbusers_requester):
    async with dbusers_requester as requester:
        # Create a user
        _, status_code = await requester("POST", "/db/guillotina/users", data=json.dumps(settings.user_data))
        assert status_code == 201

        _, status_code = await requester(
            "POST", "/db/guillotina/users", data=json.dumps(settings.second_user_data)
        )
        assert status_code == 201

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=User")
        assert status_code == 200
        assert resp["items_total"] == 2
        assert "name" in resp["items"][0]
        assert "email" in resp["items"][0]

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=User&name=user")
        assert status_code == 200
        assert resp["items_total"] == 1

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=User&name=foobar")
        assert status_code == 200
        assert resp["items_total"] == 1

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=User&name=unknownname")
        assert status_code == 200
        assert resp["items_total"] == 0

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=User&email=foo@bar.com")
        assert status_code == 200
        assert resp["items_total"] == 1

        resp, status_code = await requester(
            "GET", "/db/guillotina/@search?type_name=User&email=no-email@bar.com"
        )
        assert status_code == 200
        assert resp["items_total"] == 0


@pytest.mark.app_settings(PG_CATALOG_SETTINGS)
@pytest.mark.skipif(NOT_POSTGRES, reason="Only PG")
async def test_search_groups(dbusers_requester):
    async with dbusers_requester as requester:
        _, status_code = await requester(
            "POST", "/db/guillotina/groups", data=json.dumps(settings.group_data)
        )
        assert status_code == 201

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=Group")
        assert status_code == 200
        assert resp["items_total"] == 1
        assert "name" in resp["items"][0]

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=Group&name=foobar")
        assert status_code == 200
        assert resp["items_total"] == 1

        resp, status_code = await requester("GET", "/db/guillotina/@search?type_name=Group&name=unknownname")
        assert status_code == 200
        assert resp["items_total"] == 0
