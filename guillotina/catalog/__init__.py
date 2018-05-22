# -*- coding: utf-8 -*-
from guillotina import directives
from guillotina.interfaces import IResource
from guillotina.security.security_code import role_permission_manager
from guillotina.security.utils import get_principals_with_access_content
from guillotina.security.utils import get_roles_with_access_content
from guillotina.utils import get_content_depth
from guillotina.utils import get_content_path


global_roles_for_permission = role_permission_manager.get_roles_for_permission


directives.index_field.apply(IResource, 'uuid', type='keyword')  # pylint: disable=E1101
directives.index_field.apply(IResource, 'type_name', type='keyword')  # pylint: disable=E1101
directives.index_field.apply(IResource, 'title')  # pylint: disable=E1101
directives.index_field.apply(IResource, 'modification_date', type='date')  # pylint: disable=E1101
directives.index_field.apply(IResource, 'creation_date', type='date')  # pylint: disable=E1101


@directives.index_field.with_accessor(
    IResource, 'access_roles', type='keyword', fields=['acl'])
def get_access_roles(ob):
    roles = get_roles_with_access_content(ob)
    return roles


@directives.index_field.with_accessor(IResource, 'id', type='keyword', field='id')
def get_id(ob):
    return ob.id


@directives.index_field.with_accessor(
    IResource, 'access_users', type='keyword', fields=['acl'])
def get_access_users(ob):
    # Users that has specific access to the object
    users = get_principals_with_access_content(ob)
    return users


@directives.index_field.with_accessor(IResource, 'path', type='path')
def get_path(ob):
    return get_content_path(ob)


@directives.index_field.with_accessor(IResource, 'depth', type='int')
def get_depth(ob):
    return get_content_depth(ob)


@directives.index_field.with_accessor(IResource, 'parent_uuid', type='keyword')
def get_parent_uuid(ob):
    if hasattr(ob, '__parent__')\
            and ob.__parent__ is not None:
        return ob.__parent__.uuid


@directives.index_field.with_accessor(IResource, 'tid', type='keyword')
def get_tid(ob):
    return ob._p_serial
