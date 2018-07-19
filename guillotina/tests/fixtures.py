from guillotina import testing
from guillotina.component import get_utility
from guillotina.component import globalregistry
from guillotina.content import load_cached_schema
from guillotina.db.storages.cockroach import CockroachStorage
from guillotina.factory import make_app
from guillotina.interfaces import IApplication
from guillotina.tests.utils import ContainerRequesterAsyncContextManager
from guillotina.tests.utils import get_mocked_request
from unittest import mock
from aiohttp.test_utils import TestServer
import aiohttp
import asyncio
import os
import pytest


_dir = os.path.dirname(os.path.realpath(__file__))

IS_TRAVIS = 'TRAVIS' in os.environ
DATABASE = os.environ.get('DATABASE', 'DUMMY')

annotations = {
    'testdatabase': DATABASE,
    'travis': IS_TRAVIS
}

def base_settings_configurator(settings):
    settings["utilities"].append({
        "provides": "guillotina.interfaces.ICatalogUtility",
        "factory": "guillotina.catalog.catalog.DefaultSearchUtility"
    })


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
            settings['storages']['db'], **options,
            user='root',
            storage='cockroach')
    else:
        configure_db(settings['databases']['db'], **options)
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
                port = 5432

        annotations['pg_host'] = host
        annotations['pg_port'] = port

        yield host, port  # provide the fixture value

        if annotations['testdatabase'] == 'cockroachdb':
            pytest_docker_fixtures.cockroach_image.stop()
        elif not annotations['travis']:
            pytest_docker_fixtures.pg_image.stop()


class GuillotinaDBRequester(object):

    def __init__(self, server, loop):
        self.server = server
        self.loop = loop
        self.root = get_utility(IApplication, name='root')
        self.db = self.root['db']

    async def __call__(self, method, path, params=None, data=None, authenticated=True,
                       auth_type='Basic', headers={}, token=testing.ADMIN_TOKEN,
                       accept='application/json'):
        value, status, headers = await self.make_request(
            method, path, params, data, authenticated,
            auth_type, headers, token, accept)
        return value, status

    async def make_request(self, method, path, params=None, data=None,
                           authenticated=True, auth_type='Basic', headers={},
                           token=testing.ADMIN_TOKEN, accept='application/json'):
        settings = {}
        headers = headers.copy()
        settings['headers'] = headers
        if accept is not None:
            settings['headers']['ACCEPT'] = accept
        if authenticated and token is not None:
            settings['headers']['AUTHORIZATION'] = '{} {}'.format(
                auth_type, token)

        settings['params'] = params
        settings['data'] = data

        async with aiohttp.ClientSession(loop=self.loop) as session:
            operation = getattr(session, method.lower(), None)
            async with operation(self.server.make_url(path), **settings) as resp:
                if resp.headers.get('Content-Type') == 'application/json':
                    value = await resp.json()
                    status = resp.status
                else:
                    value = await resp.read()
                    status = resp.status
                return value, status, resp.headers


async def close_async_tasks(app):
    for clean in app.on_cleanup:
        await clean(app)


@pytest.fixture(scope='function')
def dummy_guillotina(loop):
    globalregistry.reset()
    aioapp = make_app(settings=get_dummy_settings(), loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()
    yield aioapp
    try:
        loop.run_until_complete(close_async_tasks(aioapp))
    except asyncio.CancelledError:
        pass


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


class RootAsyncContextManager(object):
    def __init__(self, request):
        self.request = request
        self.root = None
        self.txn = None

    async def __aenter__(self):
        self.txn = await self.request._tm.begin(request=dummy_request)
        self.root = await self.request._tm.get_root()
        return self.root

    async def __aexit__(self, exc_type, exc, tb):
        await self.txn.abort()


@pytest.fixture(scope='function')
async def dummy_txn_root(dummy_request):
    return RootAsyncContextManager(dummy_request)


@pytest.fixture(scope='function')
def guillotina_main(loop):
    globalregistry.reset()
    aioapp = make_app(settings=get_db_settings(), loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()
    yield aioapp
    try:
        loop.run_until_complete(close_async_tasks(aioapp))
    except asyncio.CancelledError:
        pass


@pytest.fixture(scope='function')
def guillotina(db, guillotina_main, loop):
    server = TestServer(guillotina_main)
    loop.run_until_complete(server.start_server(loop=loop))
    requester = GuillotinaDBRequester(server=server, loop=loop)
    yield requester
    loop.run_until_complete(server.close())


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
        await self.storage._pool.release(conn)
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
