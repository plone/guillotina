from guillotina import configure
from guillotina import schema
from guillotina.content import Folder
from guillotina.contrib.dbusers import _
from guillotina.directives import index_field
from guillotina.interfaces import IFolder
from zope.interface import implementer

import typing


class IGroupManager(IFolder):
    pass


class IGroup(IFolder):
    index_field("name", index_name="group_name", type="textkeyword")
    name = schema.TextLine(title=_("Group name"), required=False)

    description = schema.TextLine(title=_("Group Description"), required=False)

    index_field("user_roles", index_name="group_user_roles", type="textkeyword")
    user_roles = schema.List(title=_("Roles"), value_type=schema.TextLine(), required=False)

    index_field("users", index_name="group_users", type="textkeyword")
    users = schema.List(title=_("Users"), value_type=schema.TextLine(), required=False, default=[])


@configure.contenttype(
    type_name="Group",
    schema=IGroup,
    add_permission="guillotina.AddGroup",
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
)
class Group(Folder):
    name = description = None
    user_roles: typing.List[str] = []
    users: typing.List[str] = []

    @property
    def roles(self):
        roles = {}
        for role in getattr(self, "user_roles", []) or []:
            roles[role] = 1
        return roles

    @property
    def properties(self):
        return {}


@implementer(IGroupManager)
@configure.contenttype(
    type_name="GroupManager",
    schema=IGroupManager,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    allowed_types=["Group"],
)
class GroupManager(Folder):
    pass
