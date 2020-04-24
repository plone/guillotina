from aiohttp import hdrs
from aiohttp import test_utils
from aiohttp.helpers import noop
from aiohttp.helpers import sentinel
from aiohttp.http import HttpVersion
from aiohttp.http import RawRequestMessage
from aiohttp.web import UrlMappingMatchInfo
from contextlib import contextmanager
from guillotina import task_vars
from guillotina._settings import app_settings
from guillotina.auth.users import RootUser
from guillotina.auth.utils import set_authenticated_user
from guillotina.behaviors import apply_markers
from guillotina.content import Item
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.request import Request
from guillotina.transactions import transaction
from guillotina.utils import get_database
from multidict import CIMultiDict
from unittest import mock
from yarl import URL
from zope.interface import alsoProvides

import json
import uuid


def get_db(app, db_id):
    return app.root[db_id]


def get_mocked_request(*, db=None, method="POST", path="/", headers=None):
    headers = headers or {}
    request = make_mocked_request(method, path, headers=headers)
    request.interaction = None
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    task_vars.request.set(request)
    if db is not None:
        db.request = request
        task_vars.db.set(db)
        tm = db.get_transaction_manager()
        task_vars.tm.set(tm)
    return request


def login(*, user=RootUser("foobar")):
    set_authenticated_user(user)


def logout():
    set_authenticated_user(None)


async def get_root(*, tm=None, db=None):
    async with transaction(tm=tm, db=db) as txn:
        return await txn.manager.get_root()


async def get_container(*, requester=None, tm=None, db=None, container_id="guillotina"):
    kw = {}
    if tm is not None:
        kw["tm"] = tm
    if requester is not None:
        kw["db"] = requester.db
    if db is not None:
        kw["db"] = db
    if "db" not in kw and "tm" not in kw:
        kw["db"] = await get_database("db")
    root = await get_root(**kw)
    async with transaction(**kw):
        task_vars.db.set(kw["db"])
        container = await root.async_get(container_id)
        task_vars.registry.set(None)
        task_vars.container.set(container)
        return container


def register(ob):
    if ob.__txn__ is None:
        from guillotina.tests.mocks import FakeConnection

        conn = FakeConnection()
        conn.register(ob)


class ContainerRequesterAsyncContextManager:
    def __init__(self, guillotina):
        self.guillotina = guillotina
        self.requester = None

    async def get_requester(self):
        return self.guillotina

    async def __aenter__(self):
        self.requester = await self.get_requester()
        resp, status = await self.requester(
            "POST",
            "/db",
            data=json.dumps(
                {
                    "@type": "Container",
                    # to be able to register for tests
                    "@addons": app_settings.get("__test_addons__") or [],
                    "title": "Guillotina Container",
                    "id": "guillotina",
                    "description": "Description Guillotina Container",
                }
            ),
        )
        assert status == 200
        return self.requester

    async def __aexit__(self, exc_type, exc, tb):
        _, status = await self.requester("DELETE", "/db/guillotina")
        assert status in (200, 404)


class wrap_request:
    def __init__(self, request, func=None):
        self.request = request
        self.original = task_vars.request.get()
        self.func = func

    async def __aenter__(self):
        task_vars.request.set(self.request)
        if self.func:
            if hasattr(self.func, "__aenter__"):
                return await self.func.__aenter__()
            else:
                return await self.func()

    async def __aexit__(self, *args):
        if self.func and hasattr(self.func, "__aexit__"):
            return await self.func.__aexit__(*args)


def create_content(factory=Item, type_name="Item", id=None, parent=None, uid=None, **kw):
    obj = factory()
    obj.__parent__ = parent
    obj.type_name = type_name
    if uid is None:
        uid = uuid.uuid4().hex
    obj.__uuid__ = uid
    if id is None:
        id = f"foobar{uid}"
    obj.__name__ = obj.id = id
    apply_markers(obj)
    for attr, val in kw.items():
        setattr(obj, attr, val)
    return obj


def make_mocked_request(
    method,
    path,
    headers=None,
    *,
    version=HttpVersion(1, 1),
    closing=False,
    app=None,
    writer=sentinel,
    payload_writer=sentinel,
    protocol=sentinel,
    transport=sentinel,
    payload=sentinel,
    sslcontext=None,
    client_max_size=1024 ** 2,
):
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

    if headers is None:
        headers = {}
    if "Host" not in headers:
        headers["Host"] = "localhost"
    headers = CIMultiDict(headers)
    raw_hdrs = tuple((k.encode("utf-8"), v.encode("utf-8")) for k, v in headers.items())

    chunked = "chunked" in headers.get(hdrs.TRANSFER_ENCODING, "").lower()

    message = RawRequestMessage(
        method, path, version, headers, raw_hdrs, closing, False, False, chunked, URL(path)
    )
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

    req = Request(
        message, payload, protocol, payload_writer, time_service, task, client_max_size=client_max_size
    )

    match_info = UrlMappingMatchInfo({}, mock.Mock())
    match_info.add_app(app)
    req._match_info = match_info

    return req
