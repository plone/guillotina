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
from typing import Dict
from zope.interface import alsoProvides

import asyncio
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
        await self.guillotina.close()


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


def create_content(factory=Item, type_name="Item", id=None, parent=None, uid=None):
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
    return obj


def make_mocked_request(
    method: str,
    path: str,
    headers: Dict = None,
    query_string: bytes = b"",
    payload: bytes = b"",
    *,
    app=None,
    client_max_size=1024 ** 2,
):
    if headers is None:
        headers = {}
    if "Host" not in headers:
        headers["Host"] = "localhost"
    raw_hdrs = list((k.encode("utf-8"), v.encode("utf-8")) for k, v in headers.items())

    q: asyncio.Queue[Dict] = asyncio.Queue()
    chunks = [payload[i : i + 1024] for i in range(0, len(payload), 1024)] or [b""]
    for i, chunk in enumerate(chunks):
        q.put_nowait({"body": chunk, "more_body": i < len(chunks) - 1})

    return Request(
        "http", method, path, query_string, raw_hdrs, client_max_size=client_max_size, receive=q.get
    )
