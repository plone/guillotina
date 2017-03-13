from aiohttp.test_utils import make_mocked_request
import uuid
from guillotina.auth.users import RootUser
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.security.policy import Interaction
from zope.interface import alsoProvides
from zope.interface import implementer


def get_mocked_request(db=None):
    request = make_mocked_request('POST', '/')
    request.interaction = None
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    if db is not None:
        request._db_id = db.id
        request._db = db
        request._tm = db.new_transaction_manager()
        request._tm.request = request  # so get_current_request can find it...
    return request


def login(request):
    request.security = Interaction(request)
    request.security.add(TestParticipation(request))
    request.security.invalidate_cache()
    request._cache_groups = {}


async def get_root(request):
    await request._tm.begin(request=request)
    return await request._tm.root()


@implementer(IRequest, IDefaultLayer)
class FakeRequest(object):

    _txn_dm = None

    def __init__(self, conn=None):
        self.security = Interaction(self)
        self.headers = {}
        self._txn_dm = conn


class TestParticipation(object):

    def __init__(self, request):
        self.principal = RootUser('foobar')
        self.interaction = None


class FakeConnection(object):

    def __init__(self):
        self.containments = {}
        self.refs = {}

    async def contains(self, oid, key):
        oids = self.containments[oid]
        return key in [self.refs[oid].id for oid in oids]

    def register(self, ob):
        ob._p_jar = self
        ob._p_oid = uuid.uuid4().hex
        self.refs[ob._p_oid] = ob
        self.containments[ob._p_oid] = []
    _p_register = register


def _p_register(ob):
    if ob._p_jar is None:
        conn = FakeConnection()
        conn._p_register(ob)
