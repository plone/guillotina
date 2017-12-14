from guillotina.auth.role import check_role
from guillotina.interfaces import Allow
from guillotina.interfaces import Deny
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IRolePermissionManager
from guillotina.interfaces import Unset
from guillotina.security.permission import get_all_permissions
from guillotina.security.securitymap import SecurityMap
from zope.interface import implementer


@implementer(IPrincipalRoleManager)
class PrincipalRoleManager(SecurityMap):
    """Code mappings between principals and roles."""

    def assign_role_to_principal(self, role_id, principal_id, check=True):
        ''' See the interface IPrincipalRoleManager '''

        if check:
            check_role(None, role_id)

        self.add_cell(role_id, principal_id, Allow)

    def remove_role_from_principal(self, role_id, principal_id, check=True):
        ''' See the interface IPrincipalRoleManager '''

        if check:
            check_role(None, role_id)

        self.add_cell(role_id, principal_id, Deny)

    def unset_role_for_principal(self, role_id, principal_id):
        ''' See the interface IPrincipalRoleManager '''

        # Don't check validity intentionally.
        # After all, we certainly want to unset invalid ids.

        self.del_cell(role_id, principal_id)

    def get_principals_for_role(self, role_id):
        ''' See the interface IPrincipalRoleMap '''
        return self.get_row(role_id)

    def get_roles_for_principal(self, principal_id):
        ''' See the interface IPrincipalRoleMap '''
        return self.get_col(principal_id)

    def get_setting(self, role_id, principal_id, default=Unset):
        ''' See the interface IPrincipalRoleMap '''
        return self.query_cell(role_id, principal_id, default)

    def get_principals_and_roles(self):
        ''' See the interface IPrincipalRoleMap '''
        return self.get_all_cells()

# Roles are our rows, and principals are our columns
principal_role_manager = PrincipalRoleManager()  # noqa


@implementer(IPrincipalPermissionManager)
class PrincipalPermissionManager(SecurityMap):
    """Mappings between principals and permissions."""

    def grant_permission_to_principal(
            self, permission_id, principal_id, check=True):
        ''' See the interface IPrincipalPermissionManager '''

        self.add_cell(permission_id, principal_id, Allow)

    def grant_all_permissions_to_principal(self, principal_id):
        ''' See the interface IPrincipalPermissionManager '''

        for permission_id in get_all_permissions(None):
            self.grant_permission_to_principal(permission_id, principal_id, False)

    def deny_permission_to_principal(
            self, permission_id, principal_id,
            check=True):
        ''' See the interface IPrincipalPermissionManager '''

        self.add_cell(permission_id, principal_id, Deny)

    def unset_permission_for_principal(self, permission_id, principal_id):
        ''' See the interface IPrincipalPermissionManager '''

        # Don't check validity intentionally.
        # After all, we certianly want to unset invalid ids.

        self.del_cell(permission_id, principal_id)

    def get_principals_for_permission(self, permission_id):
        ''' See the interface IPrincipalPermissionManager '''
        return self.get_row(permission_id)

    def get_permissions_for_principal(self, principal_id):
        ''' See the interface IPrincipalPermissionManager '''
        return self.get_col(principal_id)

    def get_setting(self, permission_id, principal_id, default=Unset):
        ''' See the interface IPrincipalPermissionManager '''
        return self.query_cell(permission_id, principal_id, default)

    def get_principals_and_permissions(self):
        ''' See the interface IPrincipalPermissionManager '''
        return self.get_all_cells()


# Permissions are our rows, and principals are our columns
principal_permission_manager = PrincipalPermissionManager()


@implementer(IRolePermissionManager)
class RolePermissionManager(SecurityMap):
    """Mappings between roles and permissions."""

    def grant_permission_to_role(self, permission_id, role_id, check=True):
        '''See interface IRolePermissionMap'''

        if check:
            check_role(None, role_id)

        self.add_cell(permission_id, role_id, Allow)

    def grant_all_permissions_to_role(self, role_id):
        for permission_id in get_all_permissions(None):
            self.grant_permission_to_role(permission_id, role_id, False)

    def deny_permission_to_role(self, permission_id, role_id, check=True):
        '''See interface IRolePermissionMap'''

        if check:
            check_role(None, role_id)

        self.add_cell(permission_id, role_id, Deny)

    def unset_permission_from_role(self, permission_id, role_id):
        '''See interface IRolePermissionMap'''

        # Don't check validity intentionally.
        # After all, we certianly want to unset invalid ids.

        self.del_cell(permission_id, role_id)

    def get_roles_for_permission(self, permission_id):
        '''See interface IRolePermissionMap'''
        return self.get_row(permission_id)

    def get_permissions_for_role(self, role_id):
        '''See interface IRolePermissionMap'''
        return self.get_col(role_id)

    def get_setting(self, permission_id, role_id, default=Unset):
        '''See interface IRolePermissionMap'''
        return self.query_cell(permission_id, role_id, default)

    def get_roles_and_permissions(self):
        '''See interface IRolePermissionMap'''
        return self.get_all_cells()


# Permissions are our rows, and roles are our columns
role_permission_manager = RolePermissionManager()
