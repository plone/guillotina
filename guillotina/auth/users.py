from guillotina.interfaces import Allow
from guillotina.interfaces import IPrincipal
from zope.interface import implementer
from typing import Optional


ROOT_USER_ID = "root"
ANONYMOUS_USER_ID = "Anonymous User"


@implementer(IPrincipal)
class BaseUser:
    groups: list
    id: str
    # This is used in IGroups.get_principal() to retrieve the group by id
    _groups_cache: dict

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id}>"

    async def set_password(self, ew_password: str, old_password: Optional[str]):
        raise NotImplementedError()


class SystemUser(BaseUser):
    id = "guillotina.SystemUser"
    title = "System"
    description = ""


class RootUser(BaseUser):
    def __init__(self, password):
        self.id = ROOT_USER_ID
        self.password = password
        self.groups = ["Managers"]
        self.roles = {}
        self.properties = {}
        self.permissions = {}
        self._groups_cache = {}


class GuillotinaUser(BaseUser):
    def __init__(
        self,
        user_id="guillotina",
        groups=None,
        roles=None,
        permissions=None,
        properties=None,
        groups_cache=None,
    ):
        self.id = user_id
        self._groups = groups or []
        self._roles = roles or {}
        self._permissions = permissions or {}
        self._properties = properties or {}
        self._groups_cache = groups_cache or {}

    @property
    def groups(self):
        return self._groups

    @property
    def roles(self):
        return self._roles

    @property
    def permissions(self):
        return self._permissions

    @property
    def properties(self):
        return self._properties


class AnonymousUser(GuillotinaUser):
    def __init__(self):
        super().__init__()
        self.id = ANONYMOUS_USER_ID
        self._roles["guillotina.Anonymous"] = Allow

    @property
    def roles(self):
        # This prevents roles from being modified for anonymous user
        return self._roles.copy()
