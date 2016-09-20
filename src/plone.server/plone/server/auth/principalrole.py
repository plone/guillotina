"""Mappings between principals and roles, stored in an object locally."""
from zope.interface import implementer

from zope.securitypolicy.interfaces import IPrincipalRoleManager
from zope.securitypolicy.securitymap import AnnotationSecurityMap
from zope.securitypolicy.principalrole import AnnotationPrincipalRoleManager


@implementer(IPrincipalRoleManager)
class AnnotationPlonePrincipalRoleManager(AnnotationPrincipalRoleManager):
    """Mappings between principals and roles with global."""

    getPrincipalsForRole = AnnotationSecurityMap.getRow

    def getRolesForPrincipal(self, principal_id, request): # noqa
        """Look for global roles on request security and add global roles."""
        local_roles = self.getCol(principal_id)
        global_roles = {}
        if hasattr(request, 'security'):
            # We need to check if there is any user information that can give
            # us global roles
            for participation in request.security.participations:
                if participation.principal is not None and \
                   principal_id == participation.principal.id:
                    global_roles = participation.principal._roles.copy()
            if hasattr(request, '_cache_groups'):
                for id_group, group in request._cache_groups.items():
                    if id_group == principal_id:
                        global_roles = group._roles.copy()
        if local_roles:
            roles = global_roles.update(local_roles)
        else:
            roles = global_roles
        return [(key, value) for key, value in roles.items()]

    getPrincipalsAndRoles = AnnotationSecurityMap.getAllCells
