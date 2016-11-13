# -*- coding: utf-8 -*-
from plone.server.content import iterSchemata
from plone.server.directives import mergedTaggedValueDict
from plone.server.interfaces import DEFAULT_READ_PERMISSION
from plone.server.interfaces import DEFAULT_WRITE_PERMISSION
from plone.server.interfaces import IRequest
from plone.server.interfaces import IResource
from plone.server.interfaces import READ_PERMISSIONS_KEY
from plone.server.interfaces import WRITE_PERMISSIONS_KEY
from plone.server.transactions import get_current_request
from zope.component import adapter
from zope.interface import implementer
from zope.security._zope_security_checker import selectChecker
from zope.security.checker import _available_by_default
from zope.security.checker import CheckerPublic
from zope.security.checker import CheckerPy
from zope.security.checker import TracebackSupplement
from zope.security.interfaces import ForbiddenAttribute
from zope.security.interfaces import IChecker
from zope.security.interfaces import IInteraction
from zope.security.interfaces import Unauthorized
from zope.security.management import system_user
from zope.security.proxy import Proxy
from zope.security.proxy import removeSecurityProxy
from zope.securitypolicy.interfaces import Allow
from zope.securitypolicy.interfaces import Deny
from zope.securitypolicy.interfaces import IPrincipalPermissionMap
from zope.securitypolicy.interfaces import IPrincipalRoleMap
from zope.securitypolicy.interfaces import IRolePermissionMap
from zope.securitypolicy.interfaces import Unset
from zope.securitypolicy.principalrole import principalRoleManager
from zope.securitypolicy.zopepolicy import ZopeSecurityPolicy


globalRolesForPrincipal = principalRoleManager.getRolesForPrincipal

SettingAsBoolean = {
    Allow: True,
    Deny: False,
    Unset: None,
    None: None,
    1: True,
    0: False}

_marker = object()


@implementer(IChecker)
class ViewPermissionChecker(CheckerPy):
    def check_setattr(self, obj, name):
        if self.set_permissions:
            permission = self.set_permissions.get(name)
        else:
            permission = None

        if permission is not None:
            if permission is CheckerPublic:
                return  # Public

            request = get_current_request()
            if IInteraction(request).checkPermission(permission, obj):
                return  # allowed
            else:
                __traceback_supplement__ = (TracebackSupplement, obj)
                raise Unauthorized(obj, name, permission)

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise ForbiddenAttribute(name, obj)

    def check(self, obj, name):
        permission = self.get_permissions.get(name)
        if permission is not None:
            if permission is CheckerPublic:
                return  # Public
            request = get_current_request()
            if IInteraction(request).checkPermission(permission, obj):
                return
            else:
                __traceback_supplement__ = (TracebackSupplement, obj)
                raise Unauthorized(obj, name, permission)
        elif name in _available_by_default:
            return

        if name != '__iter__' or hasattr(obj, name):
            __traceback_supplement__ = (TracebackSupplement, obj)
            raise ForbiddenAttribute(name, obj)

    check_getattr = check

    # IChecker.proxy
    def proxy(self, obj):
        return obj
        # TODO: Figure out, how to not wrap __providedBy__, __call__ etc
        # Once they have been checked


@adapter(IRequest)
@implementer(IChecker)
class DexterityPermissionChecker(object):
    def __init__(self, request):
        self.request = request
        self.getters = {}
        self.setters = {}

    def check_getattr(self, obj, name):
        # Lookup or cached permission lookup
        portal_type = getattr(obj, 'portal_type', None)
        permission = self.getters.get((portal_type, name), _marker)

        # Lookup for the permission
        if permission is _marker:
            if name in _available_by_default:
                return
            permission = DEFAULT_READ_PERMISSION

        adapted = IResource(obj, None)

        if adapted is not None:
            for schema in iterSchemata(adapted):
                mapping = mergedTaggedValueDict(schema, READ_PERMISSIONS_KEY)
                if name in mapping:
                    permission = mapping.get(name)
                    break
            self.getters[(portal_type, name)] = permission

        if IInteraction(self.request).checkPermission(permission, obj):
            return  # has permission

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise Unauthorized(obj, name, permission)

    # IChecker.setattr
    def check_setattr(self, obj, name):
        # Lookup or cached permission lookup
        portal_type = getattr(obj, 'portal_type', None)
        permission = self.setters.get((portal_type, name), _marker)

        # Lookup for the permission
        if permission is _marker:
            if name in _available_by_default:
                return
            permission = DEFAULT_WRITE_PERMISSION

        adapted = IResource(obj, None)

        if adapted is not None:
            for schema in iterSchemata(adapted):
                mapping = mergedTaggedValueDict(schema, WRITE_PERMISSIONS_KEY)
                if name in mapping:
                    permission = mapping.get(name)
                    break
            self.setters[(portal_type, name)] = permission

        if IInteraction(self.request).checkPermission(permission, obj):
            return  # has permission

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise Unauthorized(obj, name, permission)

    # IChecker.check
    check = check_getattr

    # IChecker.proxy
    def proxy(self, obj):
        if isinstance(obj, Proxy):
            return obj
        # zope.security registered
        checker = selectChecker(obj)
        if checker is not None:
            return Proxy(obj, checker)
        return Proxy(obj, self)


@adapter(IRequest)
@implementer(IInteraction)
def getCurrentInteraction(request):
    interaction = getattr(request, 'security', None)
    if IInteraction.providedBy(interaction):
        return interaction
    return Interaction(request)


class Interaction(ZopeSecurityPolicy):
    def __init__(self, request=None):
        ZopeSecurityPolicy.__init__(self)

        if request is not None:
            self.request = request
        else:
            # Try  magic request lookup if request not given
            self.request = get_current_request()

    def checkPermission(self, permission, obj):
        # Always allow public attributes
        if permission is CheckerPublic:
            return True

        # Remove implicit security proxy (if used)
        obj = removeSecurityProxy(obj)

        # Iterate through participations ('principals')
        # and check permissions they give
        seen = {}
        for participation in self.participations:
            principal = getattr(participation, 'principal', None)

            # Invalid participation (no principal)
            if principal is None:
                continue

            # System user always has access
            if principal is system_user:
                return True

            # Speed up by skipping seen principals
            if principal.id in seen:
                continue

            # Check the permission
            if self.cached_decision(
                    obj,
                    principal.id,
                    self._groupsFor(principal),
                    permission):
                return True

            seen[principal.id] = 1  # mark as seen

        return False

    def cached_principal_roles(self, parent, principal):
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

        if parent is None:
            roles = dict(
                [(role, SettingAsBoolean[setting])
                 for (role, setting) in globalRolesForPrincipal(principal)])
            roles['plone.Anonymous'] = True  # Everybody has Anonymous
            cache_principal_roles[principal] = roles
            return roles

        roles = self.cached_principal_roles(
            removeSecurityProxy(getattr(parent, '__parent__', None)),
            principal)

        prinrole = IPrincipalRoleMap(parent, None)

        if prinrole:
            roles = roles.copy()
            for role, setting in prinrole.getRolesForPrincipal(
                    principal,
                    self.request):
                roles[role] = SettingAsBoolean[setting]

        cache_principal_roles[principal] = roles
        return roles


def getRolesWithAccessContent(obj):
    if obj is None:
        return {}
    active_roles = getRolesWithAccessContent(
        removeSecurityProxy(getattr(obj, '__parent__', None)))
    roleperm = IRolePermissionMap(obj)

    for role, permission in roleperm.getRow('plone.AccessContent'):
        active_roles[role] = permission
    return active_roles


def getPrincipalsWithAccessContent(obj):
    if obj is None:
        return {}
    active_roles = getPrincipalsWithAccessContent(
        removeSecurityProxy(getattr(obj, '__parent__', None)))
    prinperm = IPrincipalPermissionMap(obj)

    for role, permission in prinperm.getRow('plone.AccessContent'):
        active_roles[role] = permission
    return active_roles
