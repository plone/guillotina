from . import groups  # noqa
from . import users  # noqa
from guillotina import configure
from guillotina.api.content import DefaultPOST
from guillotina.content import Container
from guillotina.contrib.dbusers.content.groups import IGroupManager
from guillotina.contrib.dbusers.content.users import IUserManager

import typing as t


# override some views...
configure.service(context=IGroupManager, method="POST", permission="guillotina.AddGroup", allow_access=True)(
    DefaultPOST
)


@configure.service(context=IUserManager, method="POST", permission="guillotina.AddUser", allow_access=True)
class UserPOST(DefaultPOST):
    async def get_data(self):
        data = await super().get_data()
        if "username" in data:
            data["id"] = data["username"]
        elif "id" in data:
            data["username"] = data["id"]
        return data


class ListGroupsOrUsersService(Service):
    type_name = None

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
        return await serializer()

    async def process_catalog_obj(self, obj) -> dict:
        # TODO
        return obj

    async def _get_from_catalog(self) -> t.List[dict]:
        search = query_utility(ICatalogUtility)
        if search is None:
            raise NoCatalogException()

        result = await catalog.query(container, {"portal_type": self.type_name})
        final = []
        for obj in result["member"]:
            processed = await self.process_catalog_obj(obj)
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

        container: Container = self.context
        folder = await navigate_to(container, manager_folder)
        items = []
        async for _, obj in folder.async_items():
            processed = await self.process_obj(obj)
            items.append(processed)
        return items
