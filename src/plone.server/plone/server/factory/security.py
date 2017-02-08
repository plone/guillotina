from plone.server import configure
from plone.server.auth.users import ANONYMOUS_USER_ID
from plone.server.auth.users import ROOT_USER_ID
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from plone.server.interfaces import IPrincipalPermissionManager
from plone.server.auth.security_code import PrincipalPermissionManager


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager, trusted=True)
@configure.adapter(for_=IApplication, provides=IPrincipalPermissionManager, trusted=True)
class RootSpecialPermissions(PrincipalPermissionManager):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Plone sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, db):
        super(RootSpecialPermissions, self).__init__()
        self.grant_permission_to_principal('plone.AddPortal', ROOT_USER_ID)
        self.grant_permission_to_principal('plone.GetPortals', ROOT_USER_ID)
        self.grant_permission_to_principal('plone.DeletePortals', ROOT_USER_ID)
        self.grant_permission_to_principal('plone.AccessContent', ROOT_USER_ID)
        self.grant_permission_to_principal('plone.GetDatabases', ROOT_USER_ID)
        self.grant_permission_to_principal('plone.GetAPIDefinition', ROOT_USER_ID)
        # Access anonymous - needs to be configurable
        self.grant_permission_to_principal(
            'plone.AccessContent', ANONYMOUS_USER_ID)
