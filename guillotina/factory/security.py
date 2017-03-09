from guillotina import configure
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.security.security_code import PrincipalPermissionManager


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager)
class DatabaseSpecialPermissions(PrincipalPermissionManager):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Guillotina sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, db):
        super(DatabaseSpecialPermissions, self).__init__()
        self.grant_permission_to_principal('guillotina.AddPortal', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetPortals', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.DeletePortals', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.AccessContent', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetDatabases', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetAPIDefinition', ROOT_USER_ID)


@configure.adapter(for_=IApplication, provides=IPrincipalPermissionManager)
class ApplicationSpecialPermissions(DatabaseSpecialPermissions):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Guillotina sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, app):
        super(ApplicationSpecialPermissions, self).__init__(app)
        # Access anonymous - needs to be configurable
        # so anon can access static content mostly
        self.grant_permission_to_principal(
            'guillotina.AccessContent', ANONYMOUS_USER_ID)
