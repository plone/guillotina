from guillotina.auth import role
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IRolePermissionMap
from guillotina.security.security_code import principal_permission_manager
from guillotina.security.security_code import principal_role_manager
from guillotina.security.security_code import role_permission_manager
from guillotina.utils import get_current_request


_view_permissions = {}


def protect_view(cls, permission):
    _view_permissions[cls] = permission


def get_view_permission(cls):
    return _view_permissions.get(cls, None)


def get_roles_with_access_content(obj, request=None):
    """ Return the roles that has access to the content that are global roles"""
    if obj is None:
        return []
    if request is None:
        request = get_current_request()
    interaction = IInteraction(request)
    roles = interaction.cached_roles(obj, 'guillotina.AccessContent', 'o')
    result = []
    for r in roles.keys():
        lroles = role.global_roles()
        if r in lroles:
            result.append(r)
    return result


def get_principals_with_access_content(obj, request=None):
    if obj is None:
        return {}
    if request is None:
        request = get_current_request()
    interaction = IInteraction(request)
    roles = interaction.cached_roles(obj, 'guillotina.AccessContent', 'o')
    result = []
    for r in roles.keys():
        lroles = role.local_roles()
        if r in lroles:
            result.append(r)
    users = interaction.cached_principals(obj, result, 'guillotina.AccessContent', 'o')
    return list(users.keys())


def settings_for_object(ob):
    """Analysis tool to show all of the grants to a process
    """
    result = []
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
                for (p, r, s) in settings]

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
        for (p, r, s) in settings]

    return result
