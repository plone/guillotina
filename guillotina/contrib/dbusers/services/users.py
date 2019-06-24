from guillotina import configure
from guillotina.api.content import DefaultDELETE
from guillotina.api.content import DefaultPATCH
from guillotina.api.service import Service
from guillotina.component import get_multi_adapter
from guillotina.component import queryMultiAdapter
from guillotina.interfaces import IPATCH
from guillotina.interfaces import IContainer
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.response import HTTPNotFound
from guillotina.utils import get_authenticated_user
from guillotina.utils import navigate_to
from zope.interface import alsoProvides


@configure.service(
    context=IContainer,
    name="@user_info",
    method="GET",
    permission="guillotina.Authenticated",
)
class Info(Service):
    async def __call__(self):
        user = get_authenticated_user(self.request)
        serializer = queryMultiAdapter((user, self.request), IResourceSerializeToJson)
        if serializer:
            data = await serializer()
        else:
            data = {}
        data.update(
            {"id": user.id, "roles": user.roles, "groups": getattr(user, "groups", [])}
        )
        return data


class BaseUser(Service):
    async def get_user(self):
        user_id = self.request.matchdict["user"]
        user = await navigate_to(self.context, "users/{}".format(user_id))
        if not user:
            raise HTTPNotFound()
        return user


@configure.service(
    context=IContainer,
    name="@users/{user}",
    method="GET",
    permission="guillotina.ManageUsers",
)
class GetUsers(BaseUser):
    async def __call__(self):
        user = await self.get_user()
        serializer = get_multi_adapter(
            (user, self.request), IResourceSerializeToJsonSummary
        )
        result = await serializer()
        return result


@configure.service(
    context=IContainer,
    name="@users/{user}",
    method="PATCH",
    permission="guillotina.ManageUsers",
)
class PatchUser(BaseUser):
    async def __call__(self):
        user = await self.get_user()
        alsoProvides(self.request, IPATCH)
        view = DefaultPATCH(user, self.request)
        return await view()


@configure.service(
    context=IContainer,
    name="@users/{user}",
    method="DELETE",
    permission="guillotina.ManageUsers",
)
class DeleteUser(BaseUser):
    async def __call__(self):
        user = await self.get_user()
        view = DefaultDELETE(user, self.request)
        return await view()


@configure.service(
    context=IContainer, name="@users", method="GET", permission="guillotina.ManageUsers"
)
class ManageAvailableUsers(Service):
    async def __call__(self):
        users = await self.get_users_form_folder()
        if not users:
            return []
        result = []
        for user in users:
            serializer = get_multi_adapter(
                (user, self.request), IResourceSerializeToJsonSummary
            )
            result.append(await serializer())

        return result

    async def get_users_form_folder(self):
        user_folder = await navigate_to(self.context, "users")
        users = []
        async for _, user in user_folder.async_items():
            users.append(user)
        return users
