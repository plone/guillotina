from . import settings
from guillotina.tests.utils import get_container

import pytest


@pytest.mark.app_settings(settings.DEFAULT_SETTINGS)
async def test_users_and_groups_folders_are_created_on_install(dbusers_requester):
    async with dbusers_requester as requester:
        container = await get_container(requester=requester)
        users = await container.async_get("users")
        assert users.type_name == "UserManager"
        groups = await container.async_get("groups")
        assert groups.type_name == "GroupManager"
