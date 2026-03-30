import pytest


pytestmark = pytest.mark.asyncio

guillotina_basic_with_translations = {
    "initial_state": "private",
    "states": {
        "private": {
            "metadata": {
                "title": "Private",
                "translated_title": {
                    "en": "Private",
                    "ca": "Privat",
                    "es": "Privado",
                },
            },
            "actions": {
                "publish": {
                    "title": "Publish",
                    "metadata": {
                        "translated_title": {
                            "en": "Publish",
                            "ca": "Publicar",
                            "es": "Publicar",
                        },
                    },
                    "to": "public",
                    "check_permission": "guillotina.ReviewContent",
                }
            },
            "set_permission": {
                "roleperm": [
                    {
                        "setting": "Deny",
                        "role": "guillotina.Anonymous",
                        "permission": "guillotina.ViewContent",
                    },
                    {
                        "setting": "Deny",
                        "role": "guillotina.Anonymous",
                        "permission": "guillotina.AccessContent",
                    },
                    {
                        "setting": "Deny",
                        "role": "guillotina.Anonymous",
                        "permission": "guillotina.SearchContent",
                    },
                ]
            },
        },
        "public": {
            "metadata": {
                "title": "Public",
                "translated_title": {
                    "en": "Public",
                    "ca": "Públic",
                    "es": "Público",
                },
            },
            "actions": {
                "retire": {
                    "title": "Retire",
                    "to": "private",
                    "check_permission": "guillotina.ReviewContent",
                },
            },
            "set_permission": {
                "roleperm": [
                    {
                        "setting": "AllowSingle",
                        "role": "guillotina.Anonymous",
                        "permission": "guillotina.ViewContent",
                    },
                    {
                        "setting": "AllowSingle",
                        "role": "guillotina.Anonymous",
                        "permission": "guillotina.AccessContent",
                    },
                    {
                        "setting": "AllowSingle",
                        "role": "guillotina.Anonymous",
                        "permission": "guillotina.SearchContent",
                    },
                ]
            },
        },
    },
}


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.workflows"],
        "workflows_content": {"guillotina.interfaces.IContainer": "guillotina_basic_with_translations"},
        "workflows": {"guillotina_basic_with_translations": guillotina_basic_with_translations},
    }
)
async def test_workflow_basic(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina/@workflow")
        assert response["transitions"][0]["title"] == "Publish"
        assert response["transitions"][0]["metadata"] == {
            "translated_title": {
                "en": "Publish",
                "ca": "Publicar",
                "es": "Publicar",
            }
        }

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

        response, status = await requester("GET", "/db/guillotina/@vocabularies/workflow_states")
        assert status == 200
        assert response == {
            "@id": "http://localhost/db/guillotina/@vocabularies/workflow_states",
            "items": [
                {
                    "title": {
                        "title": "Private",
                        "translated_title": {"en": "Private", "ca": "Privat", "es": "Privado"},
                    },
                    "token": "private",
                },
                {
                    "title": {
                        "title": "Public",
                        "translated_title": {"en": "Public", "ca": "Públic", "es": "Público"},
                    },
                    "token": "public",
                },
            ],
            "items_total": 2,
        }
