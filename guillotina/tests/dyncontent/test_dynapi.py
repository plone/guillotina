from . import settings

import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_types_dyncontent(container_requester):
    async with container_requester as requester:
        resp, status_code = await requester("GET", "/db/guillotina/@types")

        assert status_code == 200
        assert "mydoc" in [x["title"] for x in resp]


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_add_dyncontent(container_requester):
    async with container_requester as requester:
        resp, status_code = await requester(
            "POST",
            "/db/guillotina",
            data=json.dumps(
                {
                    "@type": "mydoc",
                    "title": "My Doc",
                    "json_example": {"items": [1, 2, 3]},
                    "text": "Hello my friend",
                    "mysecondoption": "guillotina",
                    "mylovedlist": ["test1", "test2"],
                    "mythirdoption": "option2",
                    "guillotina.contrib.dyncontent.interfaces.Imycontextdata": {"mydata1": "My text"},
                }
            ),
        )
        assert status_code == 201

        resp, status_code = await requester("GET", "/db/guillotina/" + resp["@name"])

        assert status_code == 200
        assert len(resp["@static_behaviors"]) == 2

        resp, status_code = await requester("GET", "/db/guillotina/@types/mydoc")
        assert status_code == 200
        assert resp["properties"]["mysecondoption"]["vocabulary"] == ["guillotina", "plone"]
