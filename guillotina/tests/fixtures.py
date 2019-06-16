import asyncio
import os
from unittest import mock

import pytest
import json
import sys
from async_asgi_testclient import TestClient
from async_asgi_testclient.utils import Message
from async_asgi_testclient.utils import create_monitored_task
from async_asgi_testclient.utils import receive
from guillotina import testing
from guillotina.component import get_utility
from guillotina.component import globalregistry
from guillotina.const import ROOT_ID
from guillotina.const import TRASHED_ID
from guillotina.db.interfaces import ICockroachStorage
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.storages.cockroach import CockroachStorage
from guillotina.factory import make_app
from guillotina.interfaces import IApplication
from guillotina.tests.utils import ContainerRequesterAsyncContextManager
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login
from guillotina.tests.utils import wrap_request
from guillotina.transactions import get_tm
from guillotina.transactions import transaction
from guillotina.utils import iter_databases
from functools import partial


_dir = os.path.dirname(os.path.realpath(__file__))

IS_TRAVIS = 'TRAVIS' in os.environ
DATABASE = os.environ.get('DATABASE', 'DUMMY')
DB_SCHEMA = os.environ.get('DB_SCHEMA', 'public')

annotations = {
    'testdatabase': DATABASE,
    'test_dbschema': DB_SCHEMA,
    'travis': IS_TRAVIS
}

def base_settings_configurator(settings):
    settings["load_utilities"]['catalog'] = {
        "provides": "guillotina.interfaces.ICatalogUtility",
        "factory": "guillotina.catalog.catalog.DefaultSearchUtility"
    }


testing.configure_with(base_settings_configurator)


def get_dummy_settings():
    settings = testing.get_settings()
    settings['databases']['db']['storage'] = 'DUMMY'
    settings['databases']['db']['dsn'] = {}
    return settings


def configure_db(obj, scheme='postgres', dbname='guillotina', user='postgres',
                 host='localhost', port=5432, password='', storage='postgresql'):
    obj.update({
        'storage': storage,
        'partition': 'guillotina.interfaces.IResource'
    })
    obj['dsn'] = {
        'scheme': scheme,
        'dbname': dbname,
        'user': user,
        'host': host,
        'port': port,
        'password': password
    }


def get_db_settings():
    settings = testing.get_settings()
    if annotations['testdatabase'] == 'DUMMY':
        return settings

    settings['databases']['db']['storage'] = 'postgresql'
    settings['databases']['db']['db_schema'] = annotations['test_dbschema']

    settings['databases']['db']['dsn'] = {
        'scheme': 'postgres',
        'dbname': 'guillotina',
        'user': 'postgres',
        'host': annotations.get('pg_host', 'localhost'),
        'port': annotations.get('pg_port', 5432),
        'password': '',
    }

    options = dict(
        host=annotations.get('pg_host', 'localhost'),
        port=annotations.get('pg_port', 5432),
    )

    if annotations['testdatabase'] == 'cockroachdb':
        configure_db(
            settings['databases']['db'],
            **options,
            user='root',
            storage='cockroach')
        configure_db(
            settings['databases']['db-custom'],
            **options,
            user='root',
            storage='cockroach')
        configure_db(
            settings['storages']['db'], **options,
            user='root',
            storage='cockroach')
    else:
        configure_db(settings['databases']['db'], **options)
        configure_db(settings['databases']['db-custom'], **options)
        configure_db(settings['storages']['db'], **options)
    return settings


@pytest.fixture(scope='session')
def db():
    """
    detect travis, use travis's postgres; otherwise, use docker
    """
    if annotations['testdatabase'] == 'DUMMY':
        yield
    else:
        import pytest_docker_fixtures
        if annotations['testdatabase'] == 'cockroachdb':
            host, port = pytest_docker_fixtures.cockroach_image.run()
        else:
            if not annotations['travis']:
                host, port = pytest_docker_fixtures.pg_image.run()
            else:
                host = 'localhost'
                port = int(os.environ.get('PGPORT', 5432))

        annotations['pg_host'] = host
        annotations['pg_port'] = port

        yield host, port  # provide the fixture value

        if annotations['testdatabase'] == 'cockroachdb':
            pytest_docker_fixtures.cockroach_image.stop()
        elif not annotations['travis']:
            pytest_docker_fixtures.pg_image.stop()


class WebSocketSession:
    def __init__(self, url, headers, client):
        self.url = url
        self.headers = headers
        self.client = client
        self.input_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.output_queue: asyncio.Queue[dict] = asyncio.Queue()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.close()

    def close(self, code: int = 1000):
        self.send({"type": "websocket.disconnect", "code": code})

    def send(self, data):
        self.input_queue.put_nowait(data)

    def send_str(self, data: str) -> None:
        self.send({"type": "websocket.receive", "text": data})

    def send_bytes(self, data: bytes) -> None:
        self.send({"type": "websocket.receive", "bytes": data})

    def send_json(self, data, mode: str = "text") -> None:
        assert mode in ["text", "binary"]
        text = json.dumps(data)
        if mode == "text":
            self.send({"type": "websocket.receive", "text": text})
        else:
            self.send({"type": "websocket.receive", "bytes": text.encode("utf-8")})

    async def receive(self):
        receive_or_fail = partial(receive, self.output_queue)
        return await self.wait_response(receive_or_fail)

    async def receive_text(self) -> str:
        message = await self.receive()
        return message["text"]

    async def receive_bytes(self) -> bytes:
        message = await self.receive()
        return message["bytes"]

    async def receive_json(self, mode: str = "text"):
        assert mode in ["text", "binary"]
        message = await self.receive()
        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")
        return json.loads(text)

    def __aiter__(self):
        return self

    async def __anext__(self):
        msg = await self.receive()
        if isinstance(msg, Message):
            if msg.event == 'exit':
                raise StopAsyncIteration(msg)
        return msg

    async def connect(self):
        self.headers.update({"host": "localhost"})
        flat_headers = [
            (bytes(k.lower(), "utf8"), bytes(v, "utf8")) for k, v in self.headers.items()
        ]
        scope = {
            "type": "websocket",
            "headers": flat_headers,
            "path": self.url,
            "query_string": "",
            "root_path": "",
            "scheme": "ws",
            "subprotocols": [],
        }

        create_monitored_task(
            self.client.application(scope, self.input_queue.get, self.output_queue.put),
            self.output_queue.put_nowait
        )

        self.send({"type": "websocket.connect"})
        msg = await self.receive()
        assert msg["type"] == "websocket.accept"

    async def wait_response(self, receive_or_fail):
        message = await receive_or_fail()
        return message


class GuillotinaDBRequester(object):

    def __init__(self, client):
        self.client = client
        self.root = get_utility(IApplication, name='root')
        self.db = self.root['db']

    async def __call__(self, method, path, params=None, data=None, authenticated=True,
                       auth_type='Basic', headers={}, token=testing.ADMIN_TOKEN,
                       accept='application/json', allow_redirects=True):

        value, status, _ = await self.make_request(
            method, path, params=params, data=data, authenticated=authenticated,
            auth_type=auth_type, headers=headers, token=token,
            accept=accept, allow_redirects=allow_redirects
        )
        return value, status

    def websocket_connect(self, url, headers):
        return WebSocketSession(url, headers, self.client)

    async def make_request(self, method, path, params=None, data=None, authenticated=True,
                           auth_type='Basic', headers={}, token=testing.ADMIN_TOKEN,
                           accept='application/json', allow_redirects=True):
        settings = {}
        headers = headers.copy()
        settings['headers'] = headers
        if accept is not None:
            settings['headers']['ACCEPT'] = accept
        if authenticated and token is not None:
            settings['headers']['AUTHORIZATION'] = '{} {}'.format(
                auth_type, token)

        settings['query_string'] = params
        settings['data'] = data
        settings['allow_redirects'] = allow_redirects

        operation = getattr(self.client, method.lower(), None)
        resp = await operation(path, **settings)
        try:
            value = resp.json()
        except json.decoder.JSONDecodeError:
            value = resp.content

        status = resp.status_code
        return value, status, resp.headers

    def transaction(self, request=None):
        if request is None:
            request = get_mocked_request(self.db)
        login()
        return wrap_request(
            request, transaction(db=self.db, adopt_parent_txn=True))


@pytest.fixture(scope='function')
async def dummy_guillotina(loop):
    globalregistry.reset()
    app = make_app(settings=get_dummy_settings(), loop=loop)
    await app.startup()
    yield app
    await app.shutdown()


class DummyRequestAsyncContextManager(object):
    def __init__(self, dummy_request, loop):
        self.request = dummy_request
        self.loop = loop

    async def __aenter__(self):
        task = asyncio.Task.current_task(loop=self.loop)
        if task is not None:
            task.request = self.request
        return self.request

    async def __aexit__(self, exc_type, exc, tb):
        task = asyncio.Task.current_task(loop=self.loop)
        del task.request


@pytest.fixture(scope='function')
def dummy_request(dummy_guillotina, monkeypatch):
    from guillotina.interfaces import IApplication
    from guillotina.component import get_utility
    root = get_utility(IApplication, name='root')
    db = root['db']

    request = get_mocked_request(db)
    return request


class RootAsyncContextManager:
    def __init__(self, request):
        self.request = request
        self.root = None
        self.txn = None

    async def __aenter__(self):
        tm = get_tm()
        self.txn = await tm.begin()
        self.root = await tm.get_root()
        return self.root

    async def __aexit__(self, exc_type, exc, tb):
        await self.txn.abort()


@pytest.fixture(scope='function')
async def dummy_txn_root(dummy_request):
    return RootAsyncContextManager(dummy_request)


async def _clear_dbs(app):
    root = app.root
    # make sure to completely clear db before carrying on...
    async for db in iter_databases(root):
        storage = db.storage
        if IPostgresStorage.providedBy(storage) or ICockroachStorage.providedBy(storage):
            async with storage.pool.acquire() as conn:
                await conn.execute('''
DELETE from {}
WHERE zoid != '{}' AND zoid != '{}'
'''.format(storage._objects_table_name, ROOT_ID, TRASHED_ID))


@pytest.fixture(scope='function')
def app_client(loop):
    globalregistry.reset()
    app = make_app(settings=get_db_settings(), loop=loop)
    app.on_cleanup.insert(0, _clear_dbs)
    client = TestClient(app)
    try:
        loop.run_until_complete(client.__aenter__())
        yield app, client
    except Exception:
        loop.run_until_complete(client.__aexit__(*sys.exc_info()))
        raise
    else:
        loop.run_until_complete(client.__aexit__(None, None, None))


@pytest.fixture(scope='function')
def guillotina_main(app_client):
    app, _ = app_client
    return app


@pytest.fixture(scope='function')
def guillotina(db, app_client):
    _, client = app_client
    requester = GuillotinaDBRequester(client)
    yield requester


@pytest.fixture(scope='function')
def container_requester(guillotina):
    return ContainerRequesterAsyncContextManager(guillotina)


async def _bomb_shelter(future, timeout=2):
    try:
        return await asyncio.shield(asyncio.wait_for(future, timeout))
    except asyncio.TimeoutError:
        pass


class CockroachStorageAsyncContextManager(object):
    def __init__(self, request, loop, db):
        self.loop = loop
        self.request = request
        self.storage = None
        self.db = db

    async def __aenter__(self):
        dsn = "postgres://root:@{}:{}/guillotina?sslmode=disable".format(
            self.db[0],
            self.db[1]
        )
        self.storage = CockroachStorage(
            dsn=dsn, name='db', pool_size=25,
            conn_acquire_timeout=0.1)
        await self.storage.initialize(self.loop)
        return self.storage

    async def __aexit__(self, exc_type, exc, tb):
        conn = await self.storage.open()
        await _bomb_shelter(
            conn.execute("DROP DATABASE IF EXISTS guillotina;"))
        await _bomb_shelter(
            conn.execute("CREATE DATABASE guillotina;"))
        await self.storage.pool.release(conn)
        await self.storage.finalize()


@pytest.fixture(scope='function')
def cockroach_storage(db, dummy_request, loop):
    return CockroachStorageAsyncContextManager(dummy_request, loop, db)


@pytest.fixture(scope='function')
def command_arguments():
    arguments = mock.MagicMock()
    arguments.line_profiler = False
    arguments.monitor = False
    arguments.profile = False
    return arguments


@pytest.fixture(scope='function')
def container_command(db):
    import psycopg2
    settings = get_db_settings()
    host = settings['databases']['db']['dsn']['host']
    port = settings['databases']['db']['dsn']['port']
    conn = psycopg2.connect(f"dbname=guillotina user=postgres host={host} port={port}")
    cur = conn.cursor()
    cur.execute(open(os.path.join(_dir, "data/tables.sql"), "r").read())
    cur.execute('COMMIT;')
    cur.close()
    conn.close()
    yield {
        'settings': settings
    }

    conn = psycopg2.connect(f"dbname=guillotina user=postgres host={host} port={port}")
    cur = conn.cursor()
    cur.execute('''
DELETE FROM objects;
DELETe FROM blobs;
COMMIT;''')
