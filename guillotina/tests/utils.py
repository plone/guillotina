from aiohttp import hdrs
from aiohttp import test_utils
from aiohttp.helpers import noop
from aiohttp.helpers import sentinel
from aiohttp.http import HttpVersion
from aiohttp.http import RawRequestMessage
from aiohttp.web import UrlMappingMatchInfo
from contextlib import contextmanager
from guillotina.auth.users import RootUser
from guillotina.behaviors import apply_markers
from guillotina.content import Item
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.request import Request
from guillotina.security.policy import Interaction
from guillotina.transactions import managed_transaction
from multidict import CIMultiDict
from unittest import mock
from yarl import URL
from zope.interface import alsoProvides
from zope.interface import implementer

import json
import uuid


def get_mocked_request(db=None, method='POST', path='/', headers={}):
    request = make_mocked_request(method, path, headers=headers)
    request._futures = {}
    request._txn = None
    request.interaction = None
    request._db_write_enabled = True
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    if db is not None:
        db.request = request
        request._db_id = db.id
        request._db = db
        request._tm = db.get_transaction_manager()
        request._tm.request = request  # so get_current_request can find it...
    return request


def login(request, user=RootUser('foobar')):
    request.security = Interaction(request)
    request.security.add(TestParticipation(request, user))
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
        request._container_id = container.id
        request.container = container
        return container


@implementer(IRequest, IDefaultLayer)
class FakeRequest(object):

    _txn_dm = None

    def __init__(self, conn=None):
        self.security = Interaction(self)
        self.headers = {}
        self._txn_dm = conn


class TestParticipation(object):

    def __init__(self, request, user=RootUser('foobar')):
        self.principal = user
        self.interaction = None


def _p_register(ob):
    if ob._p_jar is None:
        from guillotina.tests.mocks import FakeConnection
        conn = FakeConnection()
        conn._p_register(ob)


class ContainerRequesterAsyncContextManager(object):
    def __init__(self, guillotina):
        self.guillotina = guillotina
        self.requester = None

    async def get_requester(self):
        return self.guillotina

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
        assert status in (200, 404)


def create_content(factory=Item, type_name='Item', id=None, parent=None):
    obj = factory()
    obj.__parent__ = parent
    obj.type_name = type_name
    obj._p_oid = uuid.uuid4().hex
    if id is None:
        id = f'foobar{uuid.uuid4().hex}'
    obj.__name__ = obj.id = id
    apply_markers(obj)
    return obj


def make_mocked_request(method, path, headers=None, *,
                        version=HttpVersion(1, 1), closing=False,
                        app=None,
                        writer=sentinel,
                        payload_writer=sentinel,
                        protocol=sentinel,
                        transport=sentinel,
                        payload=sentinel,
                        sslcontext=None,
                        client_max_size=1024**2):
    """
    XXX copied from aiohttp but using guillotina request object
    Creates mocked web.Request testing purposes.

    Useful in unit tests, when spinning full web server is overkill or
    specific conditions and errors are hard to trigger.

    """

    task = mock.Mock()
    loop = mock.Mock()
    loop.create_future.return_value = ()

    if version < HttpVersion(1, 1):
        closing = True

    if headers:
        headers = CIMultiDict(headers)
        raw_hdrs = tuple(
            (k.encode('utf-8'), v.encode('utf-8')) for k, v in headers.items())
    else:
        headers = CIMultiDict()
        raw_hdrs = ()

    chunked = 'chunked' in headers.get(hdrs.TRANSFER_ENCODING, '').lower()

    message = RawRequestMessage(
        method, path, version, headers,
        raw_hdrs, closing, False, False, chunked, URL(path))
    if app is None:
        app = test_utils._create_app_mock()

    if protocol is sentinel:
        protocol = mock.Mock()

    if transport is sentinel:
        transport = test_utils._create_transport(sslcontext)

    if writer is sentinel:
        writer = mock.Mock()
        writer.transport = transport

    if payload_writer is sentinel:
        payload_writer = mock.Mock()
        payload_writer.write_eof.side_effect = noop
        payload_writer.drain.side_effect = noop

    protocol.transport = transport
    protocol.writer = writer

    if payload is sentinel:
        payload = mock.Mock()

    time_service = mock.Mock()
    time_service.time.return_value = 12345
    time_service.strtime.return_value = "Tue, 15 Nov 1994 08:12:31 GMT"

    @contextmanager
    def timeout(*args, **kw):
        yield

    time_service.timeout = mock.Mock()
    time_service.timeout.side_effect = timeout

    req = Request(message, payload,
                  protocol, payload_writer, time_service, task,
                  client_max_size=client_max_size)

    match_info = UrlMappingMatchInfo({}, mock.Mock())
    match_info.add_app(app)
    req._match_info = match_info

    return req
