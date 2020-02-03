from guillotina import configure
from guillotina import schema
from guillotina.content import Folder
from guillotina.contrib.dbusers import _
from guillotina.directives import index_field
from guillotina.directives import read_permission
from guillotina.directives import write_permission
from guillotina.interfaces import Allow
from guillotina.interfaces import IFolder
from guillotina.interfaces import IPrincipal
from guillotina.response import HTTPUnauthorized
from guillotina.auth.validators import check_password
from guillotina.auth.validators import hash_password
from guillotina import app_settings

class IUserManager(IFolder):
    pass


class IUser(IFolder, IPrincipal):

    username = schema.TextLine(title=_("Username"), required=False)

    index_field("email", index_name="user_email", type="keyword")
    email = schema.TextLine(title=_("Email"), required=False)

    index_field("name", index_name="user_name", type="textkeyword")
    name = schema.TextLine(title=_("Name"), required=False)

    read_permission(password="guillotina.Nobody")
    password = schema.TextLine(title=_("Password"), required=False)

    write_permission(user_groups="guillotina.ManageUsers")
    user_groups = schema.List(title=_("Groups"), value_type=schema.TextLine(), required=False)

    write_permission(user_roles="guillotina.ManageUsers")
    index_field("user_roles", type="textkeyword")
    user_roles = schema.List(title=_("Roles"), value_type=schema.TextLine(), required=False)

    write_permission(user_permissions="guillotina.ManageUsers")
    user_permissions = schema.List(
        title=_("Permissions"), value_type=schema.TextLine(), required=False, default=[]
    )

    write_permission(disabled="guillotina.ManageUsers")
    disabled = schema.Bool(title=_("Disabled"), default=False)

    properties = schema.Dict(required=False, default={})


@configure.contenttype(
    type_name="User",
    schema=IUser,
    add_permission="guillotina.AddUser",
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    globally_addable=False,
)
class User(Folder):
    def __init__(self, *args, **kwargs):
        self.user_groups = []
        self.user_permissions = []
        self.user_roles = []
        self.properties = {}
        self._groups_cache = {}
        self.username = self.email = self.name = self.password = None
        self.disabled = False
        super().__init__(*args, **kwargs)

    @property
    def roles(self):
        roles = {"guillotina.Authenticated": Allow}
        for role in getattr(self, "user_roles", []) or []:
            roles[role] = Allow
        return roles

    @property
    def permissions(self):
        permissions = {}
        for permission in getattr(self, "user_permissions", []) or []:
            permissions[permission] = Allow
        return permissions

    @property
    def groups(self):
        return getattr(self, "user_groups", []) or []

    @property
    def _properties(self):
        return {}

    async def set_password(self, new_password, old_password=None):
        if old_password is not None:
            valid = check_password(self.password, old_password)
            if not valid:
                raise HTTPUnauthorized()

        self.password = hash_password(new_password)
        self.register()


@configure.contenttype(
    type_name="UserManager",
    schema=IUserManager,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    allowed_types=["User"],
    globally_addable=False,
)
class UserManager(Folder):
    pass
