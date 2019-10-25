from guillotina import configure
from guillotina.contrib.dbusers.content.groups import IGroup
from guillotina.contrib.dbusers.content.users import IUser
from guillotina.interfaces import IPATCH
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.json.serialize_content import DefaultJSONSummarySerializer
from zope.interface import Interface


@configure.adapter(for_=(IUser, Interface), provides=IResourceSerializeToJsonSummary)
class UserJSONSummarySerializer(DefaultJSONSummarySerializer):
    async def __call__(self):
        data = await super().__call__()
        data.update(
            {
                "username": self.context.username,
                "fullname": self.context.name,
                "email": self.context.email,
                "id": self.context.id,
                "location": None,
                "portrait": None,
                "roles": self.context.user_roles,
                "homepage": None,
            }
        )
        return data


@configure.adapter(for_=(IUser, IPATCH), provides=IResourceDeserializeFromJson)
class UserDeserializer:
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self, data):
        self.apply_roles(data)
        if "email" in data:
            self.context.email = data["email"]
        if "fullname" in data:
            self.context.name = data["fullname"]
        self.context.register()
        return self.context

    def apply_roles(self, data):
        if "roles" in data:
            for key, val in data["roles"].items():
                if val is False and key in self.context.user_roles:
                    self.context.user_roles.remove(key)
                elif val is True and key not in self.context.user_roles:
                    self.context.user_roles.append(key)


@configure.adapter(for_=(IGroup, Interface), provides=IResourceSerializeToJsonSummary)
class GroupSerializer(DefaultJSONSummarySerializer):
    async def __call__(self):
        data = await super().__call__()
        data.update(
            {
                "groupname": self.context.name,
                "id": self.context.id,
                "title": self.context.name,
                "roles": self.context.user_roles,
                "users": self.get_batch_users(),
            }
        )
        return data

    def get_batch_users(self):
        return {"items": self.context.users, "items_total": len(self.context.users)}


@configure.adapter(for_=(IGroup, IPATCH), provides=IResourceDeserializeFromJson)
class GroupDeserializer:
    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self, data):
        self.apply_users(data)
        self.apply_roles(data)
        if "name" in data:
            self.context.name = data["name"]
        if "description" in data:
            self.context.name = data["description"]
        self.context.register()
        return self.context

    def apply_users(self, data):
        if "users" in data:
            for key, val in data["users"].items():
                if val is False and key in self.context.users:
                    self.context.users.remove(key)
                elif val is True and key not in self.context.users:
                    self.context.users.append(key)

    def apply_roles(self, data):
        if "roles" in data:
            for key, val in data["roles"].items():
                if val is False and key in self.context.user_roles:
                    self.context.user_roles.remove(key)
                elif val is True and key not in self.context.user_roles:
                    self.context.user_roles.append(key)
