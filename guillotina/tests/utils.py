import json
import uuid
from unittest import mock

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
from multidict import CIMultiDict
from zope.interface import alsoProvides
from zope.interface import implementer


def get_db(app, db_id):
    return app.root[db_id]


def get_mocked_request(db=None, method='POST', path='/', headers={}):
    request = make_mocked_request(method, path, headers=headers)
    request._futures = {}
    request._txn = None
    request.interaction = None
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    if db is not None:
        db.request = request
        task_vars.db.set(db)
        tm = db.get_transaction_manager()
        task_vars.tm.set(tm)
    return request


def login(user=RootUser('foobar')):
    set_authenticated_user(user)


def logout():
    set_authenticated_user(None)


async def get_root(tm=None, db=None):
    async with transaction(tm=tm, db=db) as txn:
        return await txn.manager.get_root()


async def get_container(requester=None, request=None, tm=None):
    if request is None and requester is not None:
        request = get_mocked_request(requester.db)
    kw = {
        'tm': tm
    }
    if requester is not None:
        kw['db'] = requester.db
    root = await get_root(**kw)
    async with transaction(**kw):
        container = await root.async_get('guillotina')
        task_vars.container.set(container)
        return container


@implementer(IRequest, IDefaultLayer)
class FakeRequest(object):

    _txn_dm = None

    def __init__(self, conn=None):
        self.headers = {}
        self._txn_dm = conn


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
        resp, status = await self.requester('POST', '/db', data=json.dumps({
            "@type": "Container",
            # to be able to register for tests
            "@addons": app_settings.get('__test_addons__') or [],
            "title": "Guillotina Container",
            "id": "guillotina",
            "description": "Description Guillotina Container"
        }))
        assert status == 200
        return self.requester

    async def __aexit__(self, exc_type, exc, tb):
        _, status = await self.requester('DELETE', '/db/guillotina')
        assert status in (200, 404)


class wrap_request:

    def __init__(self, request, func=None):
        self.request = request
        self.original = task_vars.request.get()
        self.func = func

    async def __aenter__(self):
        task_vars.request.set(self.request)
        if self.func:
            if hasattr(self.func, '__aenter__'):
                return await self.func.__aenter__()
            else:
                return await self.func()

    async def __aexit__(self, *args):
        if self.func and hasattr(self.func, '__aexit__'):
            return await self.func.__aexit__(*args)


def create_content(factory=Item, type_name='Item', id=None, parent=None):
    obj = factory()
    obj.__parent__ = parent
    obj.type_name = type_name
    obj.__uuid__ = uuid.uuid4().hex
    if id is None:
        id = f'foobar{uuid.uuid4().hex}'
    obj.__name__ = obj.id = id
    apply_markers(obj)
    return obj


sentinel = object()


def make_mocked_request(method, path, headers=None, *,
                        writer=sentinel,
                        payload=sentinel,
                        client_max_size=1024**2):
    loop = mock.Mock()
    loop.create_future.return_value = ()

    if headers is None:
        headers = {}
    if 'Host' not in headers:
        headers['Host'] = 'localhost'
    headers = CIMultiDict(headers)
    raw_hdrs = tuple(
        (k.encode('utf-8'), v.encode('utf-8')) for k, v in headers.items())

    if payload is sentinel:
        payload = mock.Mock()

    req = Request(
        "http",
        method,
        path,
        b"",
        raw_hdrs,
        payload,
        client_max_size=client_max_size
    )

    return req
