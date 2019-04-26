from guillotina.auth import role
from guillotina.event import notify
from guillotina.interfaces import Deny
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IRolePermissionMap
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IInheritPermissionManager
from guillotina.interfaces import IInheritPermissionMap
from guillotina.interfaces import IRolePermissionManager
from guillotina.events import ObjectPermissionsModifiedEvent
from guillotina.security.security_code import principal_permission_manager
from guillotina.security.security_code import principal_role_manager
from guillotina.security.security_code import role_permission_manager
from guillotina.exceptions import PreconditionFailed

from guillotina.utils import get_current_request


def protect_view(cls, permission):
    cls.__view_permission = permission


def get_view_permission(cls):
    return getattr(cls, '__view_permission', None)


def get_roles_with_access_content(obj, request=None):
    """ Return the roles that has access to the content that are global roles"""
    if obj is None:
        return []
    if request is None:
        request = get_current_request()
    interaction = IInteraction(request)
    roles = interaction.cached_roles(obj, 'guillotina.AccessContent', 'o')
    result = []
    all_roles = role.global_roles() + role.local_roles()
    for r in roles.keys():
        if r in all_roles:
            result.append(r)
    return result


def get_principals_with_access_content(obj, request=None):
    if obj is None:
        return []
    if request is None:
        request = get_current_request()
    interaction = IInteraction(request)
    roles = interaction.cached_roles(obj, 'guillotina.AccessContent', 'o')
    result = []
    all_roles = role.global_roles() + role.local_roles()
    for r in roles.keys():
        if r in all_roles:
            result.append(r)
    users = interaction.cached_principals(obj, result, 'guillotina.AccessContent', 'o')
    return list(users.keys())


def settings_for_object(ob):
    """Analysis tool to show all of the grants to a process
    """
    result = []

    locked_permissions = []
    while ob is not None:
        data = {}
        result.append({getattr(ob, '__name__', None) or '(no name)': data})

        principal_permissions = IPrincipalPermissionMap(ob, None)
        if principal_permissions is not None:
            settings = principal_permissions.get_principals_and_permissions()
            settings.sort()
            data['prinperm'] = [
                {'principal': pr, 'permission': p, 'setting': s}
                for (p, pr, s) in settings]

        principal_roles = IPrincipalRoleMap(ob, None)
        if principal_roles is not None:
            settings = principal_roles.get_principals_and_roles()
            data['prinrole'] = [
                {'principal': p, 'role': r, 'setting': s}
                for (r, p, s) in settings]

        role_permissions = IRolePermissionMap(ob, None)
        if role_permissions is not None:
            settings = role_permissions.get_roles_and_permissions()
            data['roleperm'] = [
                {'permission': p, 'role': r, 'setting': s}
                for (p, r, s) in settings if p not in locked_permissions]

        inherit_permissions = IInheritPermissionMap(ob)
        if inherit_permissions is not None:
            settings = inherit_permissions.get_locked_permissions()
            data['perminhe'] = []
            for (p, s) in settings:
                if s is Deny:
                    locked_permissions.append(p)
                data['perminhe'].append({'permission': p, 'setting': s})

        ob = getattr(ob, '__parent__', None)

    data = {}
    result.append({'system': data})

    settings = principal_permission_manager.get_principals_and_permissions()
    settings.sort()
    data['prinperm'] = [
        {'principal': pr, 'permission': p, 'setting': s}
        for (p, pr, s) in settings]

    settings = principal_role_manager.get_principals_and_roles()
    data['prinrole'] = [
        {'principal': p, 'role': r, 'setting': s}
        for (r, p, s) in settings]

    settings = role_permission_manager.get_roles_and_permissions()
    data['roleperm'] = [
        {'permission': p, 'role': r, 'setting': s}
        for (p, r, s) in settings if p not in locked_permissions]

    return result


PermissionMap = {
    'perminhe': {
        'Allow': 'allow_inheritance',
        'Deny': 'deny_inheritance'
    },
    'prinrole': {
        'Allow': 'assign_role_to_principal',
        'Deny': 'remove_role_from_principal',
        'AllowSingle': 'assign_role_to_principal_no_inherit',
        'Unset': 'unset_role_for_principal'
    },
    'roleperm': {
        'Allow': 'grant_permission_to_role',
        'Deny': 'deny_permission_to_role',
        'AllowSingle': 'grant_permission_to_role_no_inherit',
        'Unset': 'unset_permission_from_role'
    },
    'prinperm': {
        'Allow': 'grant_permission_to_principal',
        'Deny': 'deny_permission_to_principal',
        'AllowSingle': 'grant_permission_to_principal_no_inherit',
        'Unset': 'unset_permission_for_principal'
    }
}


async def apply_sharing(context, data):
    lroles = role.local_roles()
    changed = False
    for perminhe in data.get('perminhe') or []:
        setting = perminhe.get('setting')
        if setting not in PermissionMap['perminhe']:
            raise PreconditionFailed(
                context, 'Invalid Type {}'.format(setting))
        manager = IInheritPermissionManager(context)
        operation = PermissionMap['perminhe'][setting]
        func = getattr(manager, operation)
        changed = True
        func(perminhe['permission'])

    for prinrole in data.get('prinrole') or []:
        setting = prinrole.get('setting')
        if setting not in PermissionMap['prinrole']:
            raise PreconditionFailed(
                context, 'Invalid Type {}'.format(setting))
        manager = IPrincipalRoleManager(context)
        operation = PermissionMap['prinrole'][setting]
        func = getattr(manager, operation)
        if prinrole['role'] in lroles:
            changed = True
            func(prinrole['role'], prinrole['principal'])
        else:
            raise PreconditionFailed(
                context, 'No valid local role')

    for prinperm in data.get('prinperm') or []:
        setting = prinperm['setting']
        if setting not in PermissionMap['prinperm']:
            raise PreconditionFailed(
                context, 'Invalid Type')
        manager = IPrincipalPermissionManager(context)
        operation = PermissionMap['prinperm'][setting]
        func = getattr(manager, operation)
        changed = True
        func(prinperm['permission'], prinperm['principal'])

    for roleperm in data.get('roleperm') or []:
        setting = roleperm['setting']
        if setting not in PermissionMap['roleperm']:
            raise PreconditionFailed(
                context, 'Invalid Type')
        manager = IRolePermissionManager(context)
        operation = PermissionMap['roleperm'][setting]
        func = getattr(manager, operation)
        changed = True
        func(roleperm['permission'], roleperm['role'])

    if changed:
        context._p_register()  # make sure data is saved
        await notify(ObjectPermissionsModifiedEvent(context, data))
