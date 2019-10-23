from guillotina import configure
from guillotina.api.content import DefaultDELETE
from guillotina.api.content import DefaultPATCH
from guillotina.api.service import Service
from guillotina.component import get_multi_adapter
from guillotina.interfaces import IContainer
from guillotina.interfaces import IPATCH
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.response import HTTPNotFound
from guillotina.utils import navigate_to
from zope.interface import alsoProvides

import typing as t


@configure.service(
    for_=IContainer,
    method="GET",
    name="@groups",
    permission="guillotina.ManageUsers",
    responses={
        "200": {
            "description": "Groups listing",
            # TODO: add response content schema here
        },
        "404": {"description": "Group not found"},
    },
    summary="List groups",
    allow_access=True,
)
class GetGroups(Service):
    async def __call__(self):
        groups = await self.get_all_groups()

        result = []
        for group in groups:
            serializer = get_multi_adapter((group, self.request), IResourceSerializeToJsonSummary)
            result.append(await serializer())

        return result

    async def get_all_groups(self) -> t.List[dict]:
        try:
            # Try first with catalog
            return await self._get_groups_pgcatalog()
        except NoCatalogException:
            # Slower, but does the job
            return await self._get_groups_iterating_db()

    async def _get_groups_pgcatalog(self) -> t.List[dict]:
        search = query_utility(ICatalogUtility)
        if search is None:
            raise NoCatalogException()
        # TODO; search by type_name Group
        return []

    async def _get_groups_iterating_db(self) -> t.List[dict]:
        group_folder = await navigate_to(self.context, "groups")
        groups = []
        async for _, group in group_folder.async_items():
            groups.append(group)
        return groups


class BaseGroup(Service):
    async def get_group(self):
        group_id = self.request.matchdict["group"]
        group = await navigate_to(self.context, "groups/{}".format(group_id))
        if not group:
            raise HTTPNotFound(content={"reason": f"Group {group} not found"})
        return group


@configure.service(
    for_=IContainer,
    methods="GET",
    name="@groups/{group}",
    permission="guillotina.ManageUsers",
    responses={
        "200": {
            "description": "Group",
            # TODO: add response content schema here
        },
        "404": {"description": "Group not found"},
    },
    summary="Get group data",
    allow_access=True,
)
class GetGroup(BaseGroup):
    async def __call__(self):
        group = await self.get_group()
        serializer = get_multi_adapter((group, self.request), IResourceSerializeToJsonSummary)
        return await serializer()


@configure.service(
    for_=IContainer,
    method="PATCH",
    name="@groups/{group}",
    permission="guillotina.ManageUsers",
    responses={
        "204": {"description": "Group succesfully modified"},
        "404": {"description": "Group not found"},
    },
    summary="Modify group data",
    allow_access=True,
)
class PatchGroups(BaseGroup):
    async def __call__(self):
        group = await self.get_group()
        alsoProvides(self.request, IPATCH)
        view = DefaultPATCH(group, self.request)
        return await view()


@configure.service(
    for_=IContainer,
    method="DELETE",
    name="@groups/{group}",
    permission="guillotina.ManageUsers",
    responses={
        "200": {"description": "Group succesfully deleted"},
        "404": {"description": "Group not found"},
    },
    summary="Delete a group",
    allow_access=True,
)
class DeleteGroup(BaseGroup):
    async def __call__(self):
        group = await self.get_group()
        return await DefaultDELETE(group, self.request)()


class NoCatalogException(Exception):
    pass
