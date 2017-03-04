from guillotina import configure
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.security.security_code import PrincipalPermissionManager


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager)
@configure.adapter(for_=IApplication, provides=IPrincipalPermissionManager)
class RootSpecialPermissions(PrincipalPermissionManager):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Guillotina sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, db):
        super(RootSpecialPermissions, self).__init__()
        self.grant_permission_to_principal('guillotina.AddPortal', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetPortals', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.DeletePortals', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.AccessContent', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetDatabases', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetAPIDefinition', ROOT_USER_ID)
        # Access anonymous - needs to be configurable
        self.grant_permission_to_principal(
            'guillotina.AccessContent', ANONYMOUS_USER_ID)
