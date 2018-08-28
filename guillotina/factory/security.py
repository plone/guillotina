from guillotina import configure
from guillotina import security
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.interfaces import AllowSingle
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IInheritPermissionManager
from guillotina.interfaces import IRolePermissionManager
from guillotina.security.security_code import PrincipalPermissionManager
from guillotina.security.security_code import RolePermissionManager
from guillotina.security.security_code import InheritPermissionManager


@configure.adapter(for_=IDatabase, provides=IInheritPermissionManager)
class DatabaseSpecialInheritPermissions(InheritPermissionManager):
    """This adapter will allow all inheritance.
    """

    def __init__(self, db):
        super().__init__()


@configure.adapter(for_=IApplication, provides=IInheritPermissionManager)
class ApplicationSpecialInheritPermissions(InheritPermissionManager):
    """This adapter will allow all inheritance
    """

    def __init__(self, app):
        super().__init__()


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager)
class DatabaseSpecialPermissions(PrincipalPermissionManager):
    """
    No Role Map on Application and DB so permissions set to users.
    It will not affect Guillotina containers as they don't have parent pointers to DB/APP

    We cache this because granting these permissions on every request is costly
    """

    def __init__(self, db):
        super().__init__()
        db_id = getattr(db, '__db_id__', None)
        cache_key = f'dbperms-{db_id}'
        if cache_key in security.security_map_cache:
            # an optimization since granting this is costly and it happens
            # on every single lookup.
            security.security_map_cache.apply(cache_key, self)
        else:
            self._grants()
            if db_id:
                security.security_map_cache.put(cache_key, self)

    def _grants(self):
        self.grant_permission_to_principal('guillotina.AddContainer', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetContainers', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.DeleteContainers', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.AccessContent', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetDatabases', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.MountDatabase', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.UmountDatabase', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetAPIDefinition', ROOT_USER_ID)


@configure.adapter(for_=IApplication, provides=IPrincipalPermissionManager)
class ApplicationSpecialPermissions(DatabaseSpecialPermissions):
    """
    No Role Map on Application and DB so permissions set to users.
    It will not affect Guillotina containers as they don't have parent pointers to DB/APP

    We cache this because granting these permissions on every request is costly
    """
    def __init__(self, app):
        super(DatabaseSpecialPermissions, self).__init__()
        if hasattr(app, '__cached_map__'):
            self._byrow = app.__cached_map__['byrow']
            self._bycol = app.__cached_map__['bycol']
        else:
            self._grants()
            # Access anonymous - needs to be configurable
            # so anon can access static content mostly
            self.grant_permission_to_principal(
                'guillotina.AccessContent', ANONYMOUS_USER_ID, mode=AllowSingle)
            app.__cached_map__ = {
                'byrow': self._byrow,
                'bycol': self._bycol
            }

@configure.adapter(for_=IApplication, provides=IRolePermissionManager)
class ApplicationSpecialRoles(RolePermissionManager):
    def __init__(self, app):
        super().__init__()
        self.grant_permission_to_role(
            'guillotina.AccessContent', 'guillotina.Authenticated',
            mode=AllowSingle
        )
