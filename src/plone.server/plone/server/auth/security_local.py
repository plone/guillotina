# -*- encoding: utf-8 -*-
from plone.server import configure
from plone.server.interfaces import IResource
from plone.server.interfaces import IPrincipalRoleManager
from plone.server.auth.securitymap import PloneSecurityMap
from plone.server.interfaces import Allow, Deny, Unset, AllowSingle
from plone.server.interfaces import IPrincipalPermissionManager
from plone.server.interfaces import IRolePermissionManager


@configure.adapter(
    for_=IResource,
    provides=IRolePermissionManager,
    trusted=True)
class PloneRolePermissionManager(PloneSecurityMap):
    """Provide adapter that manages role permission data in an object attribute
    """

    # the annotation key is a holdover from this module's old
    # location, but cannot change without breaking existing databases
    key = 'roleperm'

    def grant_permission_to_role(self, permission_id, role_id):
        PloneSecurityMap.add_cell(self, permission_id, role_id, Allow)

    def grant_permission_to_role_no_inherit(self, permission_id, role_id):
        PloneSecurityMap.add_cell(
            self, permission_id, role_id, AllowSingle)

    def deny_permission_to_role(self, permission_id, role_id):
        PloneSecurityMap.add_cell(self, permission_id, role_id, Deny)

    unset_permission_from_role = PloneSecurityMap.del_cell
    get_roles_for_permission = PloneSecurityMap.get_row
    get_permissions_for_role = PloneSecurityMap.get_col
    get_roles_and_permissions = PloneSecurityMap.get_all_cells

    def get_setting(self, permission_id, role_id, default=Unset):
        return PloneSecurityMap.query_cell(
            self, permission_id, role_id, default)


@configure.adapter(
    for_=IResource,
    provides=IPrincipalPermissionManager,
    trusted=True)
class PlonePrincipalPermissionManager(PloneSecurityMap):
    """Mappings between principals and permissions."""

    # the annotation key is a holdover from this module's old
    # location, but cannot change without breaking existing databases
    # It is also is misspelled, but that's OK. It just has to be unique.
    # we'll keep it as is, to prevent breaking old data:
    key = 'prinperm'

    def grant_permission_to_principal(
            self, permission_id, principal_id):
        PloneSecurityMap.add_cell(self, permission_id, principal_id, Allow)

    def grant_permission_to_principal_no_inherit(
            self, permission_id, principal_id):
        PloneSecurityMap.add_cell(
            self, permission_id, principal_id, AllowSingle)

    def deny_permission_to_principal(self, permission_id, principal_id):
        PloneSecurityMap.add_cell(self, permission_id, principal_id, Deny)

    unset_permission_for_principal = PloneSecurityMap.del_cell
    get_principals_for_permission = PloneSecurityMap.get_row
    get_permissions_for_principal = PloneSecurityMap.get_col

    def get_setting(self, permission_id, principal_id, default=Unset):
        return PloneSecurityMap.query_cell(
            self, permission_id, principal_id, default)

    get_principals_and_permissions = PloneSecurityMap.get_all_cells


@configure.adapter(
    for_=IResource,
    provides=IPrincipalRoleManager,
    trusted=True)
class PlonePrincipalRoleManager(PloneSecurityMap):
    """Mappings between principals and roles with global."""

    key = 'prinrole'

    def assign_role_to_principal(self, role_id, principal_id, inherit=True):
        PloneSecurityMap.add_cell(self, role_id, principal_id, Allow)

    def assign_role_to_principal_no_inherit(self, role_id, principal_id):
        PloneSecurityMap.add_cell(
            self, role_id, principal_id, AllowSingle)

    def remove_role_from_principal(self, role_id, principal_id):
        PloneSecurityMap.add_cell(self, role_id, principal_id, Deny)

    unset_role_for_principal = PloneSecurityMap.del_cell

    def get_setting(self, role_id, principal_id, default=Unset):
        return PloneSecurityMap.query_cell(
            self, role_id, principal_id, default)

    get_principals_and_roles = PloneSecurityMap.get_all_cells

    get_principals_for_role = PloneSecurityMap.get_row
    get_roles_for_principal = PloneSecurityMap.get_col


