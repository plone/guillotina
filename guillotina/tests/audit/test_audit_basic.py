from datetime import datetime
from datetime import timedelta
from guillotina.component import query_utility
from guillotina.contrib.audit.interfaces import IAuditUtility

import asyncio
import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.audit"]})
async def test_audit_basic(es_requester):
    async with es_requester as requester:
        response, status = await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": "audit"}))
        assert status == 200
        audit_utility = query_utility(IAuditUtility)
        # Let's check the index has been created
        resp = await audit_utility.async_es.indices.get_alias()
        assert "audit" in resp
        resp = await audit_utility.async_es.indices.get_mapping(index="audit")
        assert "path" in resp["audit"]["mappings"]["properties"]
        response, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Item", "id": "foo_item"})
        )
        assert status == 201
        await asyncio.sleep(2)
        resp, status = await requester("GET", "/db/guillotina/@audit")
        assert status == 200
        assert len(resp["hits"]["hits"]) == 2
        assert resp["hits"]["hits"][0]["_source"]["action"] == "added"
        assert resp["hits"]["hits"][0]["_source"]["type_name"] == "Container"
        assert resp["hits"]["hits"][0]["_source"]["creator"] == "root"

        assert resp["hits"]["hits"][1]["_source"]["action"] == "added"
        assert resp["hits"]["hits"][1]["_source"]["type_name"] == "Item"
        assert resp["hits"]["hits"][1]["_source"]["creator"] == "root"

        response, status = await requester("DELETE", "/db/guillotina/foo_item")
        await asyncio.sleep(2)
        resp, status = await requester("GET", "/db/guillotina/@audit")
        assert status == 200
        assert len(resp["hits"]["hits"]) == 3
        resp, status = await requester("GET", "/db/guillotina/@audit?action=removed")
        assert status == 200
        assert len(resp["hits"]["hits"]) == 1
        resp, status = await requester("GET", "/db/guillotina/@audit?action=removed&type_name=Item")
        assert status == 200
        assert len(resp["hits"]["hits"]) == 1
        resp, status = await requester("GET", "/db/guillotina/@audit?action=added&type_name=Item")
        assert status == 200
        assert len(resp["hits"]["hits"]) == 1
        assert resp["hits"]["hits"][0]["_source"]["type_name"] == "Item"
        resp, status = await requester("GET", "/db/guillotina/@audit?action=added&type_name=Container")
        assert status == 200
        assert len(resp["hits"]["hits"]) == 1
        assert resp["hits"]["hits"][0]["_source"]["type_name"] == "Container"
        creation_date = resp["hits"]["hits"][0]["_source"]["creation_date"]
        datetime_obj = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%f%z")
        new_creation_date = datetime_obj - timedelta(seconds=1)
        new_creation_date = new_creation_date.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        resp, status = await requester(
            "GET",
            f"/db/guillotina/@audit?action=added&type_name=Container&creation_date__gte={new_creation_date}",
        )  # noqa
        assert status == 200
        assert len(resp["hits"]["hits"]) == 1
        resp, status = await requester(
            "GET",
            f"/db/guillotina/@audit?action=added&type_name=Container&creation_date__lte={new_creation_date}",
        )  # noqa
        assert len(resp["hits"]["hits"]) == 0
        assert status == 200
