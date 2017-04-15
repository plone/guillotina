##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Define Zope's default security policy
"""

from guillotina import configure
from guillotina.auth.users import SystemUser
from guillotina.component import getUtility
from guillotina.interfaces import Allow
from guillotina.interfaces import AllowSingle
from guillotina.interfaces import Deny
from guillotina.interfaces import IGroups
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPrincipalPermissionMap
from guillotina.interfaces import IPrincipalRoleMap
from guillotina.interfaces import IRequest
from guillotina.interfaces import IRolePermissionMap
from guillotina.interfaces import ISecurityPolicy
from guillotina.interfaces import IView
from guillotina.interfaces import Public
from guillotina.interfaces import Unset
from guillotina.security.security_code import principal_permission_manager
from guillotina.security.security_code import principal_role_manager
from guillotina.security.security_code import role_permission_manager
from guillotina.utils import get_current_request

import zope.interface


code_principal_permission_setting = principal_permission_manager.get_setting
code_roles_for_permission = role_permission_manager.get_roles_for_permission
code_roles_for_principal = principal_role_manager.get_roles_for_principal
code_principals_for_permission = principal_permission_manager.get_principals_for_permission

SettingAsBoolean = {
    Allow: True,
    Deny: False,
    Unset: None,
    AllowSingle: 'o',
    None: None
}


def level_setting_as_boolean(level, value):
    # We want to check if its allow
    let = SettingAsBoolean[value]
    return let == level if type(let) is str else let


class CacheEntry:
    pass


@configure.adapter(
    for_=IRequest,
    provides=IInteraction)
def get_current_interaction(request):
    """
    Cache IInteraction on the request object because the request object
    is where we start adding principals
    """
    interaction = getattr(request, 'security', None)
    if IInteraction.providedBy(interaction):
        return interaction
    interaction = Interaction(request)
    request.security = interaction
    return interaction


@zope.interface.implementer(IInteraction)
@zope.interface.provider(ISecurityPolicy)
class Interaction(object):

    def __init__(self, request=None):
        self.participations = []
        self._cache = {}
        self.principal = None

        if request is not None:
            self.request = request
        else:
            # Try  magic request lookup if request not given
            self.request = get_current_request()

    def add(self, participation):
        if participation.interaction is not None:
            raise ValueError("%r already belongs to an interaction"
                             % participation)
        participation.interaction = self
        self.participations.append(participation)

    def remove(self, participation):
        if participation.interaction is not self:
            raise ValueError("%r does not belong to this interaction"
                             % participation)
        self.participations.remove(participation)
        participation.interaction = None

    def invalidate_cache(self):
        self._cache = {}

    def check_permission(self, permission, obj):
        # Always allow public attributes
        if permission is Public:
            return True

        # Iterate through participations ('principals')
        # and check permissions they give
        seen = {}
        for participation in self.participations:
            principal = getattr(participation, 'principal', None)

            # Invalid participation (no principal)
            if principal is None:
                continue

            # System user always has access
            if principal is SystemUser:
                return True

            # Speed up by skipping seen principals
            if principal.id in seen:
                continue

            self.principal = principal
            if IView.providedBy(obj):
                obj = obj.__parent__
            # Check the permission
            if self.cached_decision(
                    obj,
                    principal.id,
                    self._groups_for(principal),
                    permission):
                return True

            seen[principal.id] = 1  # mark as seen

        return False

    def cache(self, parent):
        cache = self._cache.get(id(parent))
        if cache:
            cache = cache[0]
        else:
            cache = CacheEntry()
            self._cache[id(parent)] = cache, parent
        return cache

    def cached_decision(self, parent, principal, groups, permission):
        # Return the decision for a principal and permission
        cache = self.cache(parent)
        try:
            cache_decision = cache.decision
        except AttributeError:
            cache_decision = cache.decision = {}

        cache_decision_prin = cache_decision.get(principal)
        if not cache_decision_prin:
            cache_decision_prin = cache_decision[principal] = {}

        try:
            return cache_decision_prin[permission]
        except KeyError:
            pass

        # cache_decision_prin[permission] is the cached decision for a
        # principal and permission.

        # Check direct permissions
        # First recursive function to get the permissions of a principal
        decision = self.cached_principal_permission(
            parent, principal, groups, permission, 'o')

        if decision is not None:
            cache_decision_prin[permission] = decision
            return decision

        # Check Roles permission
        # First get the Roles needed
        roles = self.cached_roles(parent, permission, 'o')
        if roles:
            # Get the roles from the user
            prin_roles = self.cached_principal_roles(
                parent, principal, groups, 'o')
            for role, setting in prin_roles.items():
                if setting and (role in roles):
                    cache_decision_prin[permission] = decision = True
                    return decision

        cache_decision_prin[permission] = decision = False
        return decision

    def cached_principal_permission(
            self, parent, principal, groups, permission, level):
        # Compute the permission, if any, for the principal.
        cache = self.cache(parent)

        try:
            cache_prin = cache.prin
        except AttributeError:
            cache_prin = cache.prin = {}

        cache_prin_per = cache_prin.get(principal)
        if not cache_prin_per:
            cache_prin_per = cache_prin[principal] = {}

        try:
            return cache_prin_per[permission]
        except KeyError:
            pass

        # We reached the end of the recursive we check global / local
        if parent is None:
            # We check the global configuration of the user and groups
            prinper = self._global_permissions_for(permission, principal)
            if prinper is None:
                cache_prin_per[permission] = prinper
                return prinper

            # If we did not found the permission for the user look at code
            prinper = SettingAsBoolean[
                code_principal_permission_setting(permission, principal, None)]
            # Now look for the group ids
            if prinper is None:
                for group in groups:
                    prinper = SettingAsBoolean[
                        code_principal_permission_setting(
                            permission, group, None)]
                    if prinper is not None:
                        continue
            cache_prin_per[permission] = prinper
            return prinper

        # Get the local map of the permissions
        # As we want to quit as soon as possible we check first locally
        prinper_map = IPrincipalPermissionMap(parent, None)
        if prinper_map is not None:
            prinper = level_setting_as_boolean(
                level, prinper_map.get_setting(permission, principal, None))
            if prinper is None:
                for group in groups:
                    prinper = level_setting_as_boolean(
                        level,
                        prinper_map.get_setting(permission, group, None))
                    if prinper is not None:
                        continue
            if prinper is not None:
                cache_prin_per[permission] = prinper
                return prinper

        # Find the permission recursivelly set to a user
        parent = getattr(parent, '__parent__', None)
        prinper = self.cached_principal_permission(
            parent, principal, groups, permission, 'p')
        cache_prin_per[permission] = prinper
        return prinper

    def global_principal_roles(self, principal, groups):
        roles = dict(
            [(role, SettingAsBoolean[setting])
                for (role, setting) in code_roles_for_principal(principal)])
        for group in groups:
            for role, settings in code_roles_for_principal(group):
                roles[role] = SettingAsBoolean[settings]
        roles['guillotina.Anonymous'] = True  # Everybody has Anonymous

        # First the global roles from user + group
        groles = self._global_roles_for(principal)
        roles.update(groles)
        return roles

    def cached_principal_roles(self, parent, principal, groups, level):
        # Redefine it to get global roles
        cache = self.cache(parent)
        try:
            cache_principal_roles = cache.principal_roles
        except AttributeError:
            cache_principal_roles = cache.principal_roles = {}
        try:
            return cache_principal_roles[principal]
        except KeyError:
            pass

        # We reached the end so we go to see the global ones
        if parent is None:
            # Then the code roles
            roles = self.global_principal_roles(principal, groups)

            cache_principal_roles[principal] = roles
            return roles

        roles = self.cached_principal_roles(
            getattr(parent, '__parent__', None),
            principal,
            groups,
            'p')

        # We check the local map of roles
        prinrole = IPrincipalRoleMap(parent, None)

        if prinrole:
            roles = roles.copy()
            for role, setting in prinrole.get_roles_for_principal(
                    principal):
                roles[role] = level_setting_as_boolean(level, setting)
            for group in groups:
                for role, setting in prinrole.get_roles_for_principal(
                        group):
                    roles[role] = level_setting_as_boolean(level, setting)

        cache_principal_roles[principal] = roles
        return roles

    def _groups_for(self, principal):
        # Right now no recursive groups
        return getattr(principal, 'groups', ())

    def cached_roles(self, parent, permission, level):
        """Get the roles for a specific permission.

        Global + Local + Code
        """
        cache = self.cache(parent)
        try:
            cache_roles = cache.roles
        except AttributeError:
            cache_roles = cache.roles = {}
        try:
            return cache_roles[permission]
        except KeyError:
            pass

        if parent is None:
            roles = dict(
                [(role, 1)
                 for (role, setting) in code_roles_for_permission(permission)
                 if setting is Allow])
            cache_roles[permission] = roles
            return roles

        roles = self.cached_roles(
            getattr(parent, '__parent__', None),
            permission, 'p')
        roleper = IRolePermissionMap(parent, None)
        if roleper:
            roles = roles.copy()
            for role, setting in roleper.get_roles_for_permission(permission):
                if setting is Allow:
                    roles[role] = 1
                elif setting is AllowSingle and level == 'o':
                    roles[role] = 1
                elif setting is Deny and role in roles:
                    del roles[role]

        if level != 'o':
            # Only cache on non 1rst level queries needs new way
            cache_roles[permission] = roles
        return roles

    def cached_principals(self, parent, roles, permission, level):
        """Get the roles for a specific permission.

        Global + Local + Code
        """
        cache = self.cache(parent)
        try:
            cache_principals = cache.principals
        except AttributeError:
            cache_principals = cache.principals = {}
        try:
            return cache_principals[permission]
        except KeyError:
            pass

        if parent is None:
            principals = dict(
                [(role, 1)
                 for (role, setting) in code_principals_for_permission(permission)
                 if setting is Allow])
            cache_principals[permission] = principals
            return principals

        principals = self.cached_principals(
            getattr(parent, '__parent__', None),
            roles,
            permission, 'p')
        prinperm = IPrincipalPermissionMap(parent, None)
        if prinperm:
            principals = principals.copy()
            for principal, setting in prinperm.get_principals_for_permission(permission):
                if setting is Allow:
                    principals[principal] = 1
                elif setting is AllowSingle and level == 'o':
                    principals[principal] = 1
                elif setting is Deny and principal in principals:
                    del principals[principal]

        prinrole = IPrincipalRoleMap(parent, None)
        if prinrole:
            for role in roles:
                for principal, setting in prinrole.get_principals_for_role(role):
                    if setting is Allow:
                        principals[principal] = 1
                    elif setting is AllowSingle and level == 'o':
                        principals[principal] = 1
                    elif setting is Deny and principal in principals:
                        del principals[principal]

        if level != 'o':
            # Only cache on non 1rst level queries needs new way
            cache_principals[permission] = principals
        return principals

    def _global_roles_for(self, principal):
        """On a principal (user/group) get global roles."""
        roles = {}
        groups = getUtility(IGroups)
        if self.principal and principal == self.principal.id:
            # Its the actual user id
            # We return all the global roles (including group)
            roles = self.principal.roles.copy()

            for group in self.principal.groups:
                roles.update(groups.get_principal(group).roles)
            return roles

        # We are asking for group id so only group roles
        if groups:
            group = groups.get_principal(principal)
            return group.roles.copy()

    def _global_permissions_for(self, principal, permission):
        """On a principal (user + group) get global permissions."""
        groups = getUtility(IGroups)
        if self.principal and principal == self.principal.id:
            # Its the actual user
            permissions = self.principal.permissions.copy()
            if permission in permissions:
                return level_setting_as_boolean('p', permissions[permission])

            for group in self.principal.groups:
                permissions = groups.get_principal(principal).permissions
                if permission in permissions:
                    return level_setting_as_boolean('p', permissions[permission])

        if groups:
            # Its a group
            permissions = groups.get_principal(principal).permissions
            if permission in permissions:
                return level_setting_as_boolean('p', permissions[permission])
        return None
