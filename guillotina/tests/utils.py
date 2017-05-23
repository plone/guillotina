from aiohttp.test_utils import make_mocked_request
from guillotina.auth.users import RootUser
from guillotina.behaviors import apply_markers
from guillotina.content import Item
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.security.policy import Interaction
from guillotina.transactions import managed_transaction
from zope.interface import alsoProvides
from zope.interface import implementer

import json
import uuid


def get_mocked_request(db=None):
    request = make_mocked_request('POST', '/')
    request._futures = {}
    request._txn = None
    request.interaction = None
    request._db_write_enabled = True
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    if db is not None:
        db._db.request = request
        request._db_id = db.id
        request._db = db
        request._tm = db.get_transaction_manager()
        request._tm.request = request  # so get_current_request can find it...
    return request


def login(request):
    request.security = Interaction(request)
    request.security.add(TestParticipation(request))
    request.security.invalidate_cache()
    request._cache_groups = {}


async def get_root(request):
    async with managed_transaction(request=request):
        return await request._tm.get_root()


async def get_container(requester=None, request=None):
    if request is None:
        request = get_mocked_request(requester.db)
    root = await get_root(request)
    async with managed_transaction(request=request):
        container = await root.async_get('guillotina')
        return container


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


class ContainerRequesterAsyncContextManager(object):
    def __init__(self, guillotina):
        self.guillotina = guillotina
        self.requester = None

    async def get_requester(self):
        return await self.guillotina

    async def __aenter__(self):
        self.requester = await self.get_requester()
        resp, status = await self.requester('POST', '/db', data=json.dumps({
            "@type": "Container",
            "title": "Guillotina Container",
            "id": "guillotina",
            "description": "Description Guillotina Container"
        }))
        assert status == 200
        return self.requester

    async def __aexit__(self, exc_type, exc, tb):
        resp, status = await self.requester('DELETE', '/db/guillotina')
        assert status == 200


def create_content(factory=Item, type_name='Item', id=None):
    obj = factory()
    obj.type_name = type_name
    obj._p_oid = uuid.uuid4().hex
    if id is None:
        id = f'foobar{uuid.uuid4().hex}'
    obj.__name__ = obj.id = id
    apply_markers(obj, None)
    return obj
