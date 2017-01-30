from plone.server import configure
from plone.server.auth.users import ANONYMOUS_USER_ID
from plone.server.auth.users import ROOT_USER_ID
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.securitypolicy.principalpermission import PrincipalPermissionManager


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager, trusted=True)
@configure.adapter(for_=IApplication, provides=IPrincipalPermissionManager, trusted=True)
class RootSpecialPermissions(PrincipalPermissionManager):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Plone sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, db):
        super(RootSpecialPermissions, self).__init__()
        self.grantPermissionToPrincipal('plone.AddPortal', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.GetPortals', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.DeletePortals', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.AccessContent', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.GetDatabases', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.GetAPIDefinition', ROOT_USER_ID)
        # Access anonymous - needs to be configurable
        self.grantPermissionToPrincipal(
            'plone.AccessContent', ANONYMOUS_USER_ID)
