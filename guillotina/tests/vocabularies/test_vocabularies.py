import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings({"applications": ["guillotina", "guillotina.contrib.vocabularies"]})
async def test_contrib_vocabulary(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina/@vocabularies")
        assert len(list(filter(lambda x: x.get("title") == "languages", response))) > 0
        assert len(list(filter(lambda x: x["title"] == "countries", response))) > 0

        response, _ = await requester("GET", "/db/guillotina/@vocabularies/languages")
        assert len(list(filter(lambda x: x.get("token") == "ca", response["items"]))) > 0

        response, _ = await requester("GET", "/db/guillotina/@vocabularies/countries")
        assert len(list(filter(lambda x: x.get("token") == "AD", response["items"]))) > 0
