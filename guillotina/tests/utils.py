from aiohttp.test_utils import make_mocked_request
from guillotina.auth.users import RootUser
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.security.policy import Interaction
from zope.interface import alsoProvides
from zope.interface import implementer


def get_mocked_request(db):
    request = make_mocked_request('POST', '/')
    request._db_id = db.id
    request._tm = db.new_transaction_manager()
    request._tm.request = request  # so get_current_request can find it...
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    return request


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
