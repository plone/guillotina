from . import settings
from guillotina import configure
from guillotina.interfaces import IFolder

import json
import pytest


pytestmark = pytest.mark.asyncio

configure.permission("dbusers.SeeTopSecret", "SeeTopSecret", "Ability to see TopSecret docs")
configure.role("dbusers.DoubleO", "00 Agent")
configure.grant(permission="dbusers.SeeTopSecret", role="dbusers.DoubleO")


@configure.service(
    context=IFolder,
    method="GET",
    permission="dbusers.SeeTopSecret",
    name="@top-secret",
)
async def top_secret(context, request):
    return {"documents": ["abcd"]}


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_roles_in_groups(dbusers_requester):

    async with dbusers_requester as requester:
        # Create the group 'top-agents' and assign the role "dbusers.DoubleO"
        resp, status = await requester(
            "POST",
            "/db/guillotina/groups",
            data=json.dumps({"id": "top-agents", "@type": "Group", "user_roles": ["dbusers.DoubleO"]}),
        )
        assert status == 201

        # Grant guillotina.AccessAcontent to role 'dbusers.DobuleO'
        _, status = await requester(
            "POST",
            "/db/guillotina/@sharing",
            data=json.dumps(
                {
                    "roleperm": [
                        {
                            "role": "dbusers.DoubleO",
                            "permission": "guillotina.AccessContent",
                            "setting": "Allow",
                        }
                    ]
                }
            ),
        )
        assert status == 200

        # Create the user and assign it to group 'top-agents'
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

        # Check the group 'top-agents' to ensure it contains the user
        resp, status = await requester("GET", "/db/guillotina/@groups/top-agents")
        assert status == 200
        assert resp["users"]["items"] == ["007"]

        # Create folder 'secrets'
        resp, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Folder", "id": "secrets"}),
        )
        assert status == 201

        # Check the default user can't access the endpoint
        # (doesn't have permission 'dbusers.SeeTopSecret')
        resp, status = await requester(
            "GET",
            "/db/guillotina/secrets/@top-secret",
        )
        assert status == 401

        # Login as James Bond
        resp, status = await requester(
            "POST", "/db/guillotina/@login", data=json.dumps({"username": "007", "password": "secret"})
        )
        assert status == 200

        # Check that James Bond has access to the Top Secret documents
        _, status = await requester(
            "GET", "/db/guillotina/secrets/@top-secret", token=resp["token"], auth_type="Bearer"
        )
        assert status == 200
