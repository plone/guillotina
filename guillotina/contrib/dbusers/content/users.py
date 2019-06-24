# -*- encoding: utf-8 -*-
from guillotina import configure
from guillotina import schema
from guillotina.content import Folder
from guillotina.contrib.dbusers import _
from guillotina.directives import read_permission
from guillotina.interfaces import Allow
from guillotina.interfaces import IFolder
from guillotina.interfaces import IPrincipal


class IUserManager(IFolder):
    pass


class IUser(IFolder, IPrincipal):

    username = schema.TextLine(
        title=_('Username'),
        required=False)

    email = schema.TextLine(
        title=_('Email'),
        required=False)

    name = schema.TextLine(
        title=_('Name'),
        required=False)

    read_permission(password='guillotina.Nobody')
    password = schema.TextLine(
        title=_('Password'),
        required=False)

    user_groups = schema.List(
        title=_('Groups'),
        value_type=schema.TextLine(),
        required=False
    )

    user_roles = schema.List(
        title=_('Roles'),
        value_type=schema.TextLine(),
        required=False
    )

    user_permissions = schema.List(
        title=_('Permissions'),
        value_type=schema.TextLine(),
        required=False,
        default=[]
    )

    disabled = schema.Bool(
        title=_('Disabled'),
        default=False
    )

    properties = schema.Dict(
        required=False,
        default={}
    )


@configure.contenttype(
    type_name="User",
    schema=IUser,
    add_permission="guillotina.AddUser",
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"])
class User(Folder):
    username = email = name = password = None
    disabled = False
    user_roles = ['guillotina.Member']
    user_groups = []
    user_permissions = {}
    properties = {}

    @property
    def roles(self):
        roles = {
            'guillotina.Authenticated': Allow
        }
        for role in getattr(self, 'user_roles', []) or []:
            roles[role] = Allow
        return roles

    @property
    def permissions(self):
        permissions = {}
        for permission in getattr(self, 'user_permissions', []) or []:
            permissions[permission] = Allow
        return permissions

    @property
    def groups(self):
        return getattr(self, 'user_groups', []) or []

    @property
    def _properties(self):
        return {}


@configure.contenttype(
    type_name="UserManager",
    schema=IUserManager,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    allowed_types=["User"])
class UserManager(Folder):
    pass
