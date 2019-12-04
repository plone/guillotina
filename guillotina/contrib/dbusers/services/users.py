from guillotina import configure
from guillotina.api.content import DefaultDELETE
from guillotina.api.content import DefaultPATCH
from guillotina.api.service import Service
from guillotina.component import get_multi_adapter
from guillotina.component import queryMultiAdapter
from guillotina.contrib.dbusers.content.users import User
from guillotina.contrib.dbusers.services.utils import ListGroupsOrUsersService
from guillotina.interfaces import IContainer
from guillotina.interfaces import IPATCH
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.response import HTTPNotFound
from guillotina.utils import get_authenticated_user
from guillotina.utils import navigate_to
from zope.interface import alsoProvides

import typing


@configure.service(
    context=IContainer,
    name="@user_info",
    permission="guillotina.AccessContent",
    method="GET",
    summary="Get info about authenticated user",
    allow_access=True,
)
class Info(Service):
    async def __call__(self):
        user = get_authenticated_user()
        serializer = queryMultiAdapter((user, self.request), IResourceSerializeToJson)
        if serializer:
            data = await serializer()
        else:
            data = {}
        data.update({"id": user.id, "roles": user.roles, "groups": getattr(user, "groups", [])})
        return data


class BaseUser(Service):
    async def get_user(self) -> User:
        user_id: str = self.request.matchdict["user"]
        try:
            user = await navigate_to(self.context, "users/{}".format(user_id))
        except KeyError:
            user = None

        if user is None:
            raise HTTPNotFound(content={"reason": f"User {user_id} not found"})
        return user


@configure.service(
    context=IContainer,
    name="@users/{user}",
    method="GET",
    permission="guillotina.ManageUsers",
    responses={
        "200": {
            "description": "User data",
            # TODO: add response content schema here
        },
        "404": {"description": "User not found"},
    },
    summary="Get user data",
    allow_access=True,
)
class GetUser(BaseUser):
    async def __call__(self) -> dict:
        user: User = await self.get_user()
        serializer = get_multi_adapter((user, self.request), IResourceSerializeToJsonSummary)
        return await serializer()


@configure.service(
    context=IContainer,
    name="@users/{user}",
    method="PATCH",
    permission="guillotina.ManageUsers",
    responses={
        "204": {"description": "User successfully modified"},
        "404": {"description": "User not found"},
    },
    summary="Modify user data",
    allow_access=True,
)
class PatchUser(BaseUser):
    async def __call__(self):
        user: User = await self.get_user()
        alsoProvides(self.request, IPATCH)
        view = DefaultPATCH(user, self.request)
        return await view()


@configure.service(
    context=IContainer,
    name="@users/{user}",
    method="DELETE",
    permission="guillotina.ManageUsers",
    responses={"200": {"description": "User successfully deleted"}, "404": {"description": "User not found"}},
    summary="Delete a user",
    allow_access=True,
)
class DeleteUser(BaseUser):
    async def __call__(self):
        user: User = await self.get_user()
        view = DefaultDELETE(user, self.request)
        return await view()


@configure.service(
    context=IContainer,
    name="@users",
    method="GET",
    permission="guillotina.ManageUsers",
    responses={
        "200": {
            "description": "List of users",
            # TODO: add response content schema here
        }
    },
    summary="List existing users",
    allow_access=True,
)
class ListUsers(ListGroupsOrUsersService):
    type_name: str = "User"
    _desired_keys: typing.List[str] = ["@name", "fullname", "email", "id", "roles"]

    async def process_catalog_obj(self, obj) -> dict:
        return {
            "@name": obj.get("@name"),
            "id": obj.get("id"),
            "fullname": obj.get("user_name"),
            "email": obj.get("user_email"),
            "roles": obj.get("user_roles") or [],
        }
