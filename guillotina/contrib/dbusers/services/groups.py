from guillotina import configure
from guillotina.api.content import DefaultDELETE
from guillotina.api.content import DefaultPATCH
from guillotina.api.service import Service
from guillotina.component import get_multi_adapter
from guillotina.content import create_content_in_container
from guillotina.contrib.dbusers.content.groups import Group
from guillotina.contrib.dbusers.services.utils import ListGroupsOrUsersService
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.interfaces import IContainer
from guillotina.interfaces import IPATCH
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPPreconditionFailed
from guillotina.utils import navigate_to
from guillotina.utils import valid_id
from zope.interface import alsoProvides

import logging
import typing


logger = logging.getLogger("guillotina.contrib.dbusers")


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
    _desired_keys: typing.List[str] = [
        "groupname",
        "id",
        "title",
        "roles",
        "users",
        "@name",
    ]

    async def process_catalog_obj(self, obj) -> dict:
        users = obj.get("group_users") or []
        users_obj = []
        for user in users:
            users_obj.append({"id": user, "title": user})
        return {
            "@name": obj.get("@name"),
            "@id": obj.get("@id"),
            "id": obj.get("id"),
            "title": obj.get("group_name"),
            "users": users,
            "members": {"items": users_obj, "items_total": len(users_obj)},  # Plone compatibility
            "roles": obj.get("group_user_roles") or [],
            "groupname": obj.get("id"),
        }


class BaseGroup(Service):
    async def get_group(self) -> Group:
        group_id: str = self.request.matchdict["group"]
        try:
            group: typing.Optional[Group] = await navigate_to(self.context, "groups/{}".format(group_id))
        except KeyError:
            group = None
        except Exception:
            logger.error("Error getting group", exc_info=True)
            group = None
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


@configure.service(
    for_=IContainer,
    method="POST",
    name="@groups",
    requestBody={
        "description": "Create a new group",
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "groupname": {
                            "type": "string",
                            "description": "Unique identifier for the group",
                        },
                        "title": {
                            "type": "string",
                            "description": "Human‐readable title of the group",
                        },
                        "description": {
                            "type": "string",
                            "description": "Longer description of the group",
                        },
                        "roles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Initial roles assigned to the group",
                        },
                    },
                    "additionalProperties": False,
                }
            }
        },
    },
    permission="guillotina.ManageUsers",
    responses={"200": {"description": "Group succesfully created"}},
    summary="Add a group",
    allow_access=True,
)
class CreateGroup(BaseGroup):
    async def __call__(self):
        data = await self.request.json()
        payload_group = {}
        _id = None
        if data.get("groupname") is not None:
            if not valid_id(data.get("groupname")):
                raise HTTPPreconditionFailed(content={"message": "The group name you entered is not valid"})
            _id = data.get("groupname").lower()

        try:
            payload_group["name"] = data.get("title") or data.get("groupname")
            payload_group["id_"] = _id
            payload_group["user_roles"] = data.get("roles", []) or []
            payload_group["description"] = data.get("description")
            payload_group["title"] = data.get("title")
            groups_folder = await self.context.async_get("groups")
            group = await create_content_in_container(
                groups_folder, "Group", **payload_group, check_security=False
            )
            await notify(ObjectAddedEvent(group))
        except KeyError:
            raise HTTPPreconditionFailed(
                content={"message": "Invalid subset. More values than current ordering"}
            )
        payload_group["id"] = group.id
        return payload_group
