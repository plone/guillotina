from guillotina.interfaces import IPrincipal
from zope.interface import implementer


ROOT_USER_ID = 'root'
ANONYMOUS_USER_ID = 'Anonymous User'


@implementer(IPrincipal)
class BaseUser(object):
    pass


class SystemUser(BaseUser):
    id = 'guillotina.SystemUser'
    title = 'System'
    description = ''


class RootUser(BaseUser):
    def __init__(self, password):
        self.id = ROOT_USER_ID
        self.password = password
        self.groups = ['Managers']
        self.roles = {}
        self.properties = {}
        self.permissions = {}


class GuillotinaUser(BaseUser):

    def __init__(self, request):
        self.id = 'guillotina'
        self.request = request
        self._groups = []
        self._roles = {}
        self._permissions = {}
        self._properties = {}

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

    def __init__(self, request):
        super(AnonymousUser, self).__init__(request)
        self.id = ANONYMOUS_USER_ID
