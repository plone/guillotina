from guillotina import configure
from guillotina.api.content import DefaultDELETE
from guillotina.api.content import DefaultPATCH
from guillotina.api.service import Service
from guillotina.component import get_multi_adapter
from guillotina.contrib.dbusers.content.groups import Group
from guillotina.contrib.dbusers.services.utils import ListGroupsOrUsersService
from guillotina.interfaces import IContainer
from guillotina.interfaces import IPATCH
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.response import HTTPNotFound
from guillotina.utils import navigate_to
from zope.interface import alsoProvides

import typing


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
class ListGroups(ListGroupsOrUsersService):
    type_name: str = "Group"
    _desired_keys: typing.List[str] = ["groupname", "id", "title", "roles", "users", "@name"]

    async def process_catalog_obj(self, obj) -> dict:
        return {
            "@name": obj.get("@name"),
            "id": obj.get("id"),
            "title": obj.get("group_name"),
            "users": obj.get("group_users") or [],
            "roles": obj.get("group_user_roles") or [],
        }


class BaseGroup(Service):
    async def get_group(self) -> Group:
        group_id: str = self.request.matchdict["group"]
        group: typing.Optional[Group] = await navigate_to(self.context, "groups/{}".format(group_id))
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
        group: Group = await self.get_group()
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
        group: Group = await self.get_group()
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
        group: Group = await self.get_group()
        return await DefaultDELETE(group, self.request)()
