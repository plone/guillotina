# -*- coding: utf-8 -*-
from guillotina.directives import index
from guillotina.interfaces import IResource
from guillotina.security.security_code import role_permission_manager
from guillotina.security.utils import get_principals_with_access_content
from guillotina.security.utils import get_roles_with_access_content
from guillotina.utils import get_content_depth
from guillotina.utils import get_content_path


global_roles_for_permission = role_permission_manager.get_roles_for_permission


index.apply(IResource, 'uuid', type='keyword')
index.apply(IResource, 'title')
index.apply(IResource, 'modification_date', type='date')
index.apply(IResource, 'creation_date', type='date')


@index.with_accessor(IResource, 'access_roles', type='keyword')
def get_access_roles(ob):
    roles = get_roles_with_access_content(ob)
    return roles


@index.with_accessor(IResource, 'id', type='keyword', field='id')
def get_id(ob):
    return ob.id


@index.with_accessor(IResource, 'access_users', type='keyword')
def get_access_users(ob):
    # Users that has specific access to the object
    users = get_principals_with_access_content(ob)
    return users


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
