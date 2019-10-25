from guillotina.exceptions import ContainerNotFound
from guillotina.utils import get_current_container


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

        return user
