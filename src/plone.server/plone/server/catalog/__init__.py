# -*- coding: utf-8 -*-
from plone.server.directives import index
from plone.server.interfaces import IResource
from plone.server.security import get_principals_with_access_content
from plone.server.security import get_roles_with_access_content
from plone.server.utils import get_content_path
from plone.server.utils import get_content_depth
from zope.securitypolicy.rolepermission import rolePermissionManager
from zope.securitypolicy.settings import Allow
from zope.securitypolicy.settings import Deny


global_roles_for_permission = rolePermissionManager.getRolesForPermission


index.apply(IResource, 'uuid', type='keyword')
index.apply(IResource, 'portal_type', type='keyword')
index.apply(IResource, 'title')
index.apply(IResource, 'modification_date', type='date')
index.apply(IResource, 'creation_date', type='date')


def get_roles(ob):
    roles = {}
    groles = global_roles_for_permission('plone.AccessContent')

    for r in groles:
        roles[r[0]] = r[1]
    lroles = get_roles_with_access_content(ob)
    roles.update(lroles)
    return roles


def get_users(ob):
    users = {}
    lusers = get_principals_with_access_content(ob)
    users.update(lusers)
    return users


@index.with_accessor(IResource, 'access_roles', type='keyword')
def get_access_roles(ob):
    roles = get_roles(ob)
    return [x for x in roles if roles[x] == Allow]


@index.with_accessor(IResource, 'access_users', type='keyword')
def get_access_users(ob):
    users = get_users(ob)
    return [x for x in users if users[x] == Allow]


@index.with_accessor(IResource, 'deny_roles', type='keyword')
def get_deny_roles(ob):
    roles = get_roles(ob)
    return [x for x in roles if roles[x] == Deny]


@index.with_accessor(IResource, 'deny_users', type='keyword')
def get_deny_users(ob):
    users = get_users(ob)
    return [x for x in users if users[x] == Deny]


@index.with_accessor(IResource, 'path', type='path')
def get_path(ob):
    return get_content_path(ob)


@index.with_accessor(IResource, 'depth', type='int')
def get_depth(ob):
    return get_content_depth(ob)


@index.with_accessor(IResource, 'parent_uuid', type='keyword')
def get_parent_uuid(ob):
    if hasattr(ob, '__parent__')\
            and ob.__parent__ is not None:
        return ob.__parent__.uuid
