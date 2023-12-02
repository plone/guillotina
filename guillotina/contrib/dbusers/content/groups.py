from guillotina import configure
from guillotina import schema
from guillotina.content import Folder
from guillotina.contrib.dbusers import _
from guillotina.directives import index_field
from guillotina.interfaces import IFolder
from guillotina.interfaces import IPrincipal
from zope.interface import implementer


class IGroupManager(IFolder):
    pass


class IGroup(IFolder, IPrincipal):
    index_field("name", type="searchabletext")
    name = schema.TextLine(title=_("Group name"), required=False)

    description = schema.TextLine(title=_("Group Description"), required=False)

    index_field("user_roles", type="textkeyword")
    user_roles = schema.List(title=_("Roles"), value_type=schema.TextLine(), required=False)

    index_field("users", type="textkeyword")
    users = schema.List(title=_("Users"), value_type=schema.TextLine(), required=False, default=[])


@configure.contenttype(
    type_name="Group",
    schema=IGroup,
    add_permission="guillotina.AddGroup",
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    globally_addable=False,
)
class Group(Folder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = self.description = None
        self.user_roles = []
        self.users = []

    @property
    def roles(self):
        roles = {}
        for role in getattr(self, "user_roles", []) or []:
            roles[role] = 1
        return roles

    @property
    def permissions(self):
        return {}

    @property
    def properties(self):
        return {}


@implementer(IGroupManager)
@configure.contenttype(
    type_name="GroupManager",
    schema=IGroupManager,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    allowed_types=["Group"],
    globally_addable=False,
)
class GroupManager(Folder):
    pass
