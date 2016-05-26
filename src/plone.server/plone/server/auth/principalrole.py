"""Mappings between principals and roles, stored in an object locally.
"""
from zope.interface import implementer

from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.securitymap import AnnotationSecurityMap
from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager


@implementer(IPrincipalRoleManager)
class AnnotationPlonePrincipalRoleManager(AnnotationPrincipalRoleManager):
    """Mappings between principals and roles with global."""

    getPrincipalsForRole = AnnotationSecurityMap.getRow

    def getRolesForPrincipal(self, principal_id, request):
        local_roles = self.getCol(principal_id)
        global_roles = {}
        if hasattr(request, '_cache_user') and \
                principal_id == request._cache_user.id:
            global_roles = request._cache_user._roles.copy()
        if local_roles:
            roles = global_roles.update(local_roles)
        else:
            roles = global_roles
        return [(key, value) for key, value in roles.items()]

    getPrincipalsAndRoles = AnnotationSecurityMap.getAllCells

