from guillotina.api.service import Service
from guillotina.catalog.catalog import DefaultSearchUtility
from guillotina.component import get_multi_adapter
from guillotina.component import query_utility
from guillotina.content import Container
from guillotina.interfaces import IAsyncContainer
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.utils import navigate_to

import typing as t


class ListGroupsOrUsersService(Service):
    type_name: t.Optional[str] = None
    _desired_keys: t.List[str] = []

    async def __call__(self) -> t.List[dict]:
        self.check_type_name()
        try:
            # Try first with catalog
            return await self._get_from_catalog()
        except NoCatalogException:
            # Slower, but does the job
            return await self._get_from_db()

    async def process_db_obj(self, obj) -> dict:
        serializer = get_multi_adapter((obj, self.request), IResourceSerializeToJsonSummary)
        result: dict = await serializer()
        # Cleanup keys other than desired
        final: dict = {k: v for k, v in result.items() if k in self._desired_keys}
        return final

    async def process_catalog_obj(self, obj) -> dict:
        raise NotImplementedError()

    async def _get_from_catalog(self) -> t.List[dict]:
        catalog = query_utility(ICatalogUtility)

        if catalog.__class__ == DefaultSearchUtility:
            # DefaultSearchUtility does nothing
            raise NoCatalogException()

        container: Container = self.context
        result = await catalog.query(container, {"portal_type": self.type_name})
        final: t.List = []
        for obj in result["member"]:
            processed: dict = await self.process_catalog_obj(obj)
            final.append(processed)
        return final

    def check_type_name(self):
        if not self.type_name or self.type_name not in ("Group", "User"):
            raise Exception("Wrong type_name")

    async def _get_from_db(self) -> t.List[dict]:
        if self.type_name == "Group":
            manager_folder = "groups"
        elif self.type_name == "User":
            manager_folder = "users"

        container: IAsyncContainer = self.context
        folder = await navigate_to(container, manager_folder)
        items = []
        async for _, obj in folder.async_items():
            processed = await self.process_db_obj(obj)
            items.append(processed)
        return items


class NoCatalogException(Exception):
    pass
