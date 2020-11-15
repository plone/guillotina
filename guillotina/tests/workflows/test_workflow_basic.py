import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.workflows"],
        "workflows_content": {"guillotina.interfaces.IContainer": "guillotina_basic"},
    }
)
async def test_workflow_basic(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina/@workflow")
        assert response["transitions"][0]["title"] == "Publish"

        response, _ = await requester("GET", "/db/guillotina")
        assert response["review_state"] == "private"

        response, status = await requester("GET", "/db/guillotina", token=None)
        assert status == 401

        response, _ = await requester("GET", "/db/guillotina/@sharing")
        assert response["local"]["roleperm"]["guillotina.Anonymous"]["guillotina.AccessContent"] == "Deny"

        response, _ = await requester("POST", "/db/guillotina/@workflow/publish")
        assert response["actor"] == "root"
        assert response["title"] == "Publish"

        response, _ = await requester("GET", "/db/guillotina")
        assert response["review_state"] == "public"

        response, _ = await requester("GET", "/db/guillotina/@sharing")
        assert (
            response["local"]["roleperm"]["guillotina.Anonymous"]["guillotina.AccessContent"] == "AllowSingle"
        )

        response, status = await requester("GET", "/db/guillotina", token=None)
        assert status == 200
