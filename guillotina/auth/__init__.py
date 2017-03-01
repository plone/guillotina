from guillotina import app_settings
from guillotina.auth.users import ROOT_USER_ID
from guillotina.utils import resolve_or_get
from zope.security.proxy import removeSecurityProxy
from zope.security.interfaces import IInteraction
from guillotina.interfaces import IRolePermissionMap
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.auth.security_code import principal_permission_manager
from guillotina.auth.security_code import role_permission_manager
from guillotina.auth.security_code import principal_role_manager
from . import groups
from . import role
from guillotina.transactions import get_current_request


async def authenticate_request(request):
    for policy in app_settings['auth_extractors']:
        policy = resolve_or_get(policy)
        token = await policy(request).extract_token()
        if token:
            for validator in app_settings['auth_token_validators']:
                validator = resolve_or_get(validator)
                if (validator.for_validators is not None and
                        policy.name not in validator.for_validators):
                    continue
                user = await validator(request).validate(token)
                if user is not None:
                    return user


async def find_user(request, token):
    if token.get('id') == ROOT_USER_ID:
        return request.application.root_user
    for identifier in app_settings['auth_user_identifiers']:
        identifier = resolve_or_get(identifier)
        user = await identifier(request).get_user(token)
        if user is not None:
            return user


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
        result.append((getattr(ob, '__name__', '(no name)'), data))

        principalPermissions = IPrincipalPermissionMap(ob, None)
        if principalPermissions is not None:
            settings = principalPermissions.get_principals_and_permissions()
            settings.sort()
            data['principalPermissions'] = [
                {'principal': pr, 'permission': p, 'setting': s}
                for (p, pr, s) in settings]

        principalRoles = IPrincipalRoleMap(ob, None)
        if principalRoles is not None:
            settings = principalRoles.get_principals_and_roles()
            data['principalRoles'] = [
                {'principal': p, 'role': r, 'setting': s}
                for (r, p, s) in settings]

        rolePermissions = IRolePermissionMap(ob, None)
        if rolePermissions is not None:
            settings = rolePermissions.get_roles_and_permissions()
            data['rolePermissions'] = [
                {'permission': p, 'role': r, 'setting': s}
                for (p, r, s) in settings]

        ob = getattr(ob, '__parent__', None)

    data = {}
    result.append(('code settings', data))

    settings = principal_permission_manager.get_principals_and_permissions()
    settings.sort()
    data['principalPermissions'] = [
        {'principal': pr, 'permission': p, 'setting': s}
        for (p, pr, s) in settings]

    settings = principal_role_manager.get_principals_and_roles()
    data['principalRoles'] = [
        {'principal': p, 'role': r, 'setting': s}
        for (r, p, s) in settings]

    settings = role_permission_manager.get_roles_and_permissions()
    data['rolePermissions'] = [
        {'permission': p, 'role': r, 'setting': s}
        for (p, r, s) in settings]

    return result
