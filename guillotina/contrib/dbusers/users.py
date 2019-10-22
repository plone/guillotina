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
            return

        if user_id not in await users.async_keys():
            return

        user = await users.async_get(user_id)
        if user.disabled:
            return

        return user
