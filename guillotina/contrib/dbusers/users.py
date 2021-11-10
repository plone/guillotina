from .services.utils import NoCatalogException
from guillotina.component import query_utility
from guillotina.contrib.catalog.pg.utility import PGSearchUtility
from guillotina.exceptions import ContainerNotFound
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import IPrincipal
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.transactions import get_transaction
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


class EmailDBUserIdentifier:
    """Identifier of users by email.
    This method only works with pgcatalog active.
    """

    async def get_user(self, token: typing.Dict) -> typing.Optional[IPrincipal]:
        try:
            container = get_current_container()
            users = await container.async_get("users")
        except (AttributeError, KeyError, ContainerNotFound):
            return None

        catalog = query_utility(ICatalogUtility)
        if not isinstance(catalog, PGSearchUtility):
            raise NoCatalogException()

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        conn = await txn.get_connection()
        # The catalog doesn't work because we are still
        # not authenticated
        sql = f"""
            SELECT id FROM
                {txn.storage.objects_table_name}
            WHERE
              json->>'type_name' = 'User'
              AND parent_id != 'DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD'
              AND json->>'container_id' = $1::varchar
              AND lower(json->>'user_email') = lower($2::varchar)
        """
        async with txn.lock:
            row = await conn.fetchrow(sql, container.id, token.get("id"))
        if not row:
            return None

        user = await users.async_get(row["id"])
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
