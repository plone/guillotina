from guillotina import configure
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.security.security_code import PrincipalPermissionManager


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager)
class DatabaseSpecialPermissions(PrincipalPermissionManager):
    """
    No Role Map on Application and DB so permissions set to users.
    It will not affect Guillotina containers as they don't have parent pointers to DB/APP

    We cache this because granting these permissions on every request is costly
    """

    __cached__db_maps = {}

    def __init__(self, db):
        super(DatabaseSpecialPermissions, self).__init__()
        db_id = getattr(db, '__db_id__', None)
        if db_id in self.__cached__db_maps:
            # an optimization since granting this is costly and it happens
            # on every single lookup.
            self._byrow = self.__cached__db_maps[db.__db_id__]['byrow']
            self._bycol = self.__cached__db_maps[db.__db_id__]['bycol']
        else:
            self._grants()
            if db_id:
                self.__cached__db_maps[db.__db_id__] = {
                    'byrow': self._byrow,
                    'bycol': self._bycol
                }

    def _grants(self):
        self.grant_permission_to_principal('guillotina.AddContainer', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetContainers', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.DeleteContainers', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.AccessContent', ROOT_USER_ID)
        self.grant_permission_to_principal('guillotina.GetDatabases', ROOT_USER_ID)
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
                'guillotina.AccessContent', ANONYMOUS_USER_ID)
            app.__cached_map__ = {
                'byrow': self._byrow,
                'bycol': self._bycol
            }
