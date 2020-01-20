from . import settings
from guillotina import configure
from guillotina.interfaces import IFolder

import json
import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_roles_in_groups(dbusers_requester):
    configure.permission("dbusers.SeeTopSecret", "SeeTopSecret", "Ability to see TopSecret docs")
    configure.role("dbusers.DoubleO", "00 Agent")
    configure.grant(permission="dbusers.SeeTopSecret", role="dbusers.DoubleO")

    @configure.service(
        context=IFolder, method="GET", permission="dbusers.SeeTopSecret", name="@top-secret",
    )
    async def top_secret(context, request):
        return {"documents": ["abcd"]}

    async with dbusers_requester as requester:
        resp, status = await requester(
            "POST",
            "/db/guillotina/groups",
            data=json.dumps({"id": "top-agents", "@type": "Group", "user_roles": ["dbusers.DoubleO"],}),
        )
        assert status == 201
        resp, status = await requester("GET", "/db/guillotina/@groups")
        assert status == 200
        assert len(resp) == 1
        assert resp[0]["roles"] == ["dbusers.DoubleO"]

        # create the user
        resp, status = await requester(
            "POST",
            "/db/guillotina/users",
            data=json.dumps(
                {
                    "@type": "User",
                    "id": "007",
                    "name": "James Bond",
                    "username": "007",
                    "password": "secret",
                    "user_groups": ["top-agents"],
                }
            ),
        )
        assert status == 201

        resp, status = await requester("GET", "/db/guillotina/@groups/top-agents")
        assert status == 200
        assert resp["users"]["items"] == ["007"]

        # Create folder 'secret's
        resp, status = await requester(
            "POST", "/db/guillotina/", data=json.dumps({"@type": "Folder", "id": "secrets"}),
        )
        assert status == 201

        # resp, status = await requester(
        #     "GET",
        #     "/db/guillotina/secrets/@top-secret",
        # )
        # assert status == 404

        # Login as new user
        resp, status_code = await requester(
            "POST", "/db/guillotina/@login", data=json.dumps({"username": "007", "password": "secret"})
        )
        assert status_code == 200

        # User should have access to its own folder
        _, status_code = await requester(
            "GET", "/db/guillotina/secrets/@top-secret", token=resp["token"], auth_type="Bearer"
        )
        assert status_code == 200
