from aiohttp.client_exceptions import ContentTypeError
from aiohttp.test_utils import TestServer
from guillotina import app_settings
from guillotina import task_vars
from guillotina import testing
from guillotina.component import get_utility
from guillotina.component import globalregistry
from guillotina.const import ROOT_ID
from guillotina.const import TRASHED_ID
from guillotina.content import load_cached_schema
from guillotina.db.interfaces import ICockroachStorage
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.storages.cockroach import CockroachStorage
from guillotina.factory import make_app
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.tests import mocks
from guillotina.tests.utils import ContainerRequesterAsyncContextManager
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login
from guillotina.tests.utils import logout
from guillotina.tests.utils import wrap_request
from guillotina.transactions import get_tm
from guillotina.transactions import transaction
from guillotina.utils import merge_dicts
from unittest import mock

import aiohttp
import asyncio
import json
import os
import pytest


_dir = os.path.dirname(os.path.realpath(__file__))

IS_TRAVIS = "TRAVIS" in os.environ
DATABASE = os.environ.get("DATABASE", "DUMMY")
DB_SCHEMA = os.environ.get("DB_SCHEMA", "public")

annotations = {"testdatabase": DATABASE, "test_dbschema": DB_SCHEMA, "redis": None, "travis": IS_TRAVIS}


def base_settings_configurator(settings):
    settings["load_utilities"]["catalog"] = {
        "provides": "guillotina.interfaces.ICatalogUtility",
        "factory": "guillotina.catalog.catalog.DefaultSearchUtility",
    }


testing.configure_with(base_settings_configurator)


def get_dummy_settings(pytest_node=None):
    settings = testing.get_settings()
    settings = _update_from_pytest_markers(settings, pytest_node)
    settings["databases"]["db"]["storage"] = "DUMMY"
    settings["databases"]["db"]["dsn"] = {}
    return settings


def configure_db(
    obj,
    scheme="postgres",
    dbname="guillotina",
    user="postgres",
    host="localhost",
    port=5432,
    password="",
    storage="postgresql",
):
    obj.update({"storage": storage, "partition": "guillotina.interfaces.IResource"})
    obj["dsn"] = {
        "scheme": scheme,
        "dbname": dbname,
        "user": user,
        "host": host,
        "port": port,
        "password": password,
    }


def _update_from_pytest_markers(settings, pytest_node):
    if not pytest_node:
        return settings

    # Update test app settings from pytest markers
    marks = []
    try:
        marks.extend([mark for mark in pytest_node.iter_markers(name="app_settings")])
    except AttributeError:
        # Older pytest versions
        mark = pytest_node.get_marker("app_settings")
        if mark is not None:
            marks.append(mark)

    for mark in marks:
        to_update = mark.args[0]
        settings = merge_dicts(settings, to_update)

    return settings


def get_db_settings(pytest_node=None):
    settings = testing.get_settings()
    settings = _update_from_pytest_markers(settings, pytest_node)
    if annotations["redis"] is not None:
        if "redis" not in settings:
            settings["redis"] = {}
        settings["redis"]["host"] = annotations["redis"][0]
        settings["redis"]["port"] = annotations["redis"][1]

    if annotations["testdatabase"] == "DUMMY":
        return settings

    settings["databases"]["db"]["storage"] = "postgresql"
    settings["databases"]["db"]["db_schema"] = annotations["test_dbschema"]

    settings["databases"]["db"]["dsn"] = {
        "scheme": "postgres",
        "dbname": annotations.get("pg_db", "guillotina"),
        "user": "postgres",
        "host": annotations.get("pg_host", "localhost"),
        "port": annotations.get("pg_port", 5432),
        "password": "",
    }

    options = dict(
        host=annotations.get("pg_host", "localhost"),
        port=annotations.get("pg_port", 5432),
        dbname=annotations.get("pg_db", "guillotina"),
    )

    if annotations["testdatabase"] == "cockroachdb":
        configure_db(settings["databases"]["db"], **options, user="root", storage="cockroach")
        configure_db(settings["databases"]["db-custom"], **options, user="root", storage="cockroach")
        configure_db(settings["storages"]["db"], **options, user="root", storage="cockroach")
    else:
        configure_db(settings["databases"]["db"], **options)
        configure_db(settings["databases"]["db-custom"], **options)
        configure_db(settings["storages"]["db"], **options)

    return settings


@pytest.fixture(scope="session")
def db():
    """
    detect travis, use travis's postgres; otherwise, use docker
    """
    if annotations["testdatabase"] == "DUMMY":
        yield
    else:
        import pytest_docker_fixtures

        if annotations["testdatabase"] == "cockroachdb":
            host, port = pytest_docker_fixtures.cockroach_image.run()
        else:
            if not annotations["travis"]:
                host, port = pytest_docker_fixtures.pg_image.run()
            else:
                host = "localhost"
                port = int(os.environ.get("PGPORT", 5432))

        annotations["pg_host"] = host
        annotations["pg_port"] = port

        yield host, port  # provide the fixture value

        if annotations["testdatabase"] == "cockroachdb":
            pytest_docker_fixtures.cockroach_image.stop()
        elif not annotations["travis"]:
            pytest_docker_fixtures.pg_image.stop()


class GuillotinaDBRequester(object):
    def __init__(self, server, loop):
        self.server = server
        self.loop = loop
        self.root = get_utility(IApplication, name="root")
        self.db = self.root["db"]

    async def __call__(
        self,
        method,
        path,
        params=None,
        data=None,
        authenticated=True,
        auth_type="Basic",
        headers=None,
        token=testing.ADMIN_TOKEN,
        accept="application/json",
        allow_redirects=True,
    ):
        if headers is None:
            headers = {}
        value, status, headers = await self.make_request(
            method,
            path,
            params,
            data,
            authenticated,
            auth_type,
            headers,
            token,
            accept,
            allow_redirects=allow_redirects,
        )
        return value, status

    async def make_request(
        self,
        method,
        path,
        params=None,
        data=None,
        authenticated=True,
        auth_type="Basic",
        headers=None,
        token=testing.ADMIN_TOKEN,
        accept="application/json",
        allow_redirects=True,
    ):
        if headers is None:
            headers = {}
        settings = {}
        headers = headers.copy()
        settings["headers"] = headers
        if accept is not None:
            settings["headers"]["ACCEPT"] = accept
        if authenticated and token is not None:
            settings["headers"]["AUTHORIZATION"] = "{} {}".format(auth_type, token)

        settings["params"] = params
        settings["data"] = data
        settings["allow_redirects"] = allow_redirects

        async with aiohttp.ClientSession(loop=self.loop) as session:
            operation = getattr(session, method.lower(), None)
            async with operation(self.server.make_url(path), **settings) as resp:
                try:
                    value = await resp.json()
                except ContentTypeError:
                    value = await resp.read()

                status = resp.status
                return value, status, resp.headers

    def transaction(self, request=None):
        if request is None:
            request = get_mocked_request(db=self.db)
        login()
        return wrap_request(request, transaction(db=self.db, adopt_parent_txn=True))


async def close_async_tasks(app):
    for clean in app.on_cleanup:
        await clean(app)
    # clear all task_vars
    for var in (
        "request",
        "txn",
        "tm",
        "futures",
        "authenticated_user",
        "security_policies",
        "container",
        "registry",
        "db",
    ):
        getattr(task_vars, var).set(None)


@pytest.fixture(scope="function")
def dummy_guillotina(loop, request):
    globalregistry.reset()
    aioapp = loop.run_until_complete(make_app(settings=get_dummy_settings(request.node), loop=loop))
    aioapp.config.execute_actions()
    load_cached_schema()
    yield aioapp
    try:
        loop.run_until_complete(close_async_tasks(aioapp))
    except asyncio.CancelledError:  # pragma: no cover
        pass
    logout()


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


@pytest.fixture(scope="function")
def dummy_request(dummy_guillotina, monkeypatch):
    from guillotina.interfaces import IApplication
    from guillotina.component import get_utility

    root = get_utility(IApplication, name="root")
    db = root["db"]

    request = get_mocked_request(db=db)
    task_vars.request.set(request)
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


@pytest.fixture(scope="function")
async def dummy_txn_root(dummy_request):
    return RootAsyncContextManager(dummy_request)


@pytest.fixture(scope="function")
def mock_txn():
    txn = mocks.MockTransaction()
    task_vars.txn.set(txn)
    yield txn
    task_vars.txn.set(None)


async def _clear_dbs(root):
    # make sure to completely clear db before carrying on...
    for _, db in root:
        if not IDatabase.providedBy(db):
            continue
        storage = db.storage
        if IPostgresStorage.providedBy(storage) or ICockroachStorage.providedBy(storage):
            async with storage.pool.acquire() as conn:
                await conn.execute(
                    """
DELETE from {}
WHERE zoid != '{}' AND zoid != '{}'
""".format(
                        storage._objects_table_name, ROOT_ID, TRASHED_ID
                    )
                )
                await conn.execute(
                    """
SELECT 'DROP INDEX ' || string_agg(indexrelid::regclass::text, ', ')
   FROM   pg_index  i
   LEFT   JOIN pg_depend d ON d.objid = i.indexrelid
                          AND d.deptype = 'i'
   WHERE  i.indrelid = '{}'::regclass
   AND    d.objid IS NULL
""".format(
                        storage._objects_table_name
                    )
                )


@pytest.fixture(scope="function")
def guillotina_main(loop, request):
    globalregistry.reset()
    aioapp = loop.run_until_complete(make_app(settings=get_db_settings(request.node), loop=loop))
    aioapp.config.execute_actions()
    load_cached_schema()

    loop.run_until_complete(_clear_dbs(aioapp.root))

    yield aioapp

    logout()
    try:
        loop.run_until_complete(close_async_tasks(aioapp))
    except asyncio.CancelledError:  # pragma: no cover
        pass


@pytest.fixture(scope="function")
def guillotina(db, guillotina_main, loop):
    server_settings = app_settings.get("test_server_settings", {})
    server = TestServer(guillotina_main, **server_settings)

    loop.run_until_complete(server.start_server(loop=loop))
    requester = GuillotinaDBRequester(server=server, loop=loop)
    yield requester
    loop.run_until_complete(server.close())


@pytest.fixture(scope="function")
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
        dsn = "postgres://root:@{}:{}/guillotina?sslmode=disable".format(self.db[0], self.db[1])
        self.storage = CockroachStorage(dsn=dsn, name="db", pool_size=25, conn_acquire_timeout=0.1)
        await self.storage.initialize(self.loop)
        return self.storage

    async def __aexit__(self, exc_type, exc, tb):
        async with self.storage.pool.acquire() as conn:
            await _bomb_shelter(conn.execute("DROP DATABASE IF EXISTS guillotina;"))
            await _bomb_shelter(conn.execute("CREATE DATABASE guillotina;"))
            try:
                await self.storage.finalize()
            except asyncio.CancelledError:  # pragma: no cover
                pass


@pytest.fixture(scope="function")
def cockroach_storage(db, dummy_request, loop):
    return CockroachStorageAsyncContextManager(dummy_request, loop, db)


@pytest.fixture(scope="function")
def command_arguments():
    arguments = mock.MagicMock()
    arguments.line_profiler = False
    arguments.monitor = False
    arguments.profile = False
    return arguments


@pytest.fixture(scope="function")
def container_command(db):
    import psycopg2  # type: ignore

    settings = get_db_settings()
    host = settings["databases"]["db"]["dsn"]["host"]
    port = settings["databases"]["db"]["dsn"]["port"]
    conn = psycopg2.connect(f"dbname=guillotina user=postgres host={host} port={port}")
    cur = conn.cursor()
    cur.execute(open(os.path.join(_dir, "data/tables.sql"), "r").read())
    cur.execute("COMMIT;")
    cur.close()
    conn.close()
    yield {"settings": settings}

    conn = psycopg2.connect(f"dbname=guillotina user=postgres host={host} port={port}")
    cur = conn.cursor()
    cur.execute(
        """
DELETE FROM objects;
DELETe FROM blobs;
COMMIT;"""
    )


@pytest.fixture(scope="session")
def redis_container():
    import pytest_docker_fixtures

    host, port = pytest_docker_fixtures.redis_image.run()
    annotations["redis"] = (host, port)
    yield host, port  # provide the fixture value
    pytest_docker_fixtures.redis_image.stop()
    annotations["redis"] = None


class DBUsersRequester(ContainerRequesterAsyncContextManager):
    async def __aenter__(self):
        requester = await super().__aenter__()
        await requester("POST", "/db/guillotina/@addons", data=json.dumps({"id": "dbusers"}))
        return requester


@pytest.fixture(scope="function")
async def dbusers_requester(guillotina):
    return DBUsersRequester(guillotina)
