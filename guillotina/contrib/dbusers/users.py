from guillotina.auth.groups import GuillotinaGroup
from guillotina.exceptions import ContainerNotFound
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to


class DBUserIdentifier:
    async def get_user(self, token):
        """Returns the current user associated with the token and None if user
        could not be found.

        """
        try:
            container = get_current_container()
            users = await container.async_get("users")
        except (AttributeError, KeyError, ContainerNotFound):
            return

        user_id = token.get("id", "")
        if not user_id:
            # No user id in the token
            return

        if not await users.async_contains(user_id):
            # User id does not correspond to any existing user folder
            return

        user = await users.async_get(user_id)
        if user.disabled:
            # User is disabled
            return

        if not hasattr(user, "_groups_cache"):
            user._groups_cache = {}

        # load groups
        for ident in user.groups:
            try:
                group = await navigate_to(container, f"groups/{ident}")
            except KeyError:
                continue

            user._groups_cache[ident] = GuillotinaGroup(ident, roles=group.roles)

        return user
