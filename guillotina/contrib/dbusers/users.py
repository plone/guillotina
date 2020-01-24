from guillotina.exceptions import ContainerNotFound
from guillotina.interfaces import IPrincipal
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to

import typing


class DBUserIdentifier:
    async def get_user(self, token: typing.Dict) -> typing.Optional[IPrincipal]:
        """Returns the current user associated with the token and None if user
        could not be found.

        """
        try:
            container = get_current_container()
            users = await container.async_get("users")
        except (AttributeError, KeyError, ContainerNotFound):
            return None

        user_id = token.get("id", "")
        if not user_id:
            # No user id in the token
            return None

        if not await users.async_contains(user_id):
            # User id does not correspond to any existing user folder
            return None

        user = await users.async_get(user_id)
        if user.disabled:
            # User is disabled
            return None

        # Load groups into cache
        for ident in user.groups:
            try:
                user._groups_cache[ident] = await navigate_to(container, f"groups/{ident}")
            except KeyError:
                continue

        return user
