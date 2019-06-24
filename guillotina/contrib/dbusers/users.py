from guillotina.exceptions import ContainerNotFound
from guillotina.utils import get_current_container


class DBUserIdentifier:
    async def get_user(self, token):
        try:
            container = get_current_container()
            users = await container.async_get("users")
        except (AttributeError, KeyError, ContainerNotFound):
            return

        user_ids = await users.async_keys()
        if token.get("id", "") in user_ids:
            user = await users.async_get(token.get("id", ""))
            if not user.disabled:
                return user
