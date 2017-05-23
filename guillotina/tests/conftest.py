# -*- coding: utf-8 -*-
from guillotina.component import getUtility
from guillotina.content import load_cached_schema
from guillotina.db.storages.cockroach import CockroachStorage
from guillotina.db.transaction import HARD_CACHE
from guillotina.factory import make_app
from guillotina.interfaces import IApplication
from guillotina.testing import ADMIN_TOKEN
from guillotina.testing import TESTING_SETTINGS
from guillotina.tests import docker_containers as containers
from guillotina.tests.utils import ContainerRequesterAsyncContextManager
from guillotina.tests.utils import get_mocked_request

import aiohttp
import asyncio
import copy
import os
import pytest
import sys


IS_TRAVIS = 'TRAVIS' in os.environ
USE_COCKROACH = 'USE_COCKROACH' in os.environ

PG_SETTINGS = copy.deepcopy(TESTING_SETTINGS)
PG_SETTINGS['databases'][0]['db']['storage'] = 'postgresql'

PG_SETTINGS['databases'][0]['db']['partition'] = \
    'guillotina.interfaces.IResource'
PG_SETTINGS['databases'][0]['db']['dsn'] = {
    'scheme': 'postgres',
    'dbname': 'guillotina',
    'user': 'postgres',
    'host': 'localhost',
    'password': '',
    'port': 5432
}
if USE_COCKROACH:
    PG_SETTINGS['databases'][0]['db']['storage'] = 'cockroach'
    PG_SETTINGS['databases'][0]['db']['dsn'].update({
        'user': 'root',
        'port': 26257
    })

DUMMY_SETTINGS = copy.deepcopy(TESTING_SETTINGS)
DUMMY_SETTINGS['databases'][0]['db']['storage'] = 'DUMMY'

DUMMY_SETTINGS['databases'][0]['db']['partition'] = \
    'guillotina.interfaces.IResource'
DUMMY_SETTINGS['databases'][0]['db']['dsn'] = {}


@pytest.fixture(scope='session')
def postgres():
    """
    detect travis, use travis's postgres; otherwise, use docker
    """
    sys._db_tests = True

    if USE_COCKROACH:
        host = containers.cockroach_image.run()
    else:
        if not IS_TRAVIS:
            host = containers.postgres_image.run()
        else:
            host = 'localhost'

    PG_SETTINGS['databases'][0]['db']['dsn']['host'] = host

    yield host  # provide the fixture value

    if USE_COCKROACH:
        containers.cockroach_image.stop()
    elif not IS_TRAVIS:
        containers.postgres_image.stop()


@pytest.fixture(scope='session')
def etcd():
    host = containers.etcd_image.run()

    yield host  # provide the fixture value

    containers.etcd_image.stop()


class GuillotinaDBRequester(object):

    def __init__(self, server, loop):
        self.server = server
        self.loop = loop
        self.root = getUtility(IApplication, name='root')
        self.db = self.root['db']

    async def __call__(self, method, path, params=None, data=None, authenticated=True,
                       auth_type='Basic', headers={}, token=ADMIN_TOKEN, accept='application/json'):
        value, status, headers = await self.make_request(
            method, path, params, data, authenticated,
            auth_type, headers, token, accept)
        return value, status

    async def make_request(self, method, path, params=None, data=None,
                           authenticated=True, auth_type='Basic', headers={},
                           token=ADMIN_TOKEN, accept='application/json'):
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
                try:
                    value = await resp.json()
                    status = resp.status
                except:  # noqa
                    value = await resp.read()
                    status = resp.status
                return value, status, resp.headers


@pytest.fixture(scope='function')
def dummy_guillotina(loop):
    from guillotina import test_package  # noqa
    aioapp = make_app(settings=DUMMY_SETTINGS, loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()
    return aioapp


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
    HARD_CACHE.clear()
    from guillotina.interfaces import IApplication
    from guillotina.component import getUtility
    root = getUtility(IApplication, name='root')
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
    HARD_CACHE.clear()
    return RootAsyncContextManager(dummy_request)


@pytest.fixture(scope='function')
def guillotina_main(loop):
    HARD_CACHE.clear()
    from guillotina import test_package  # noqa
    aioapp = make_app(settings=PG_SETTINGS, loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()
    yield aioapp


@pytest.fixture(scope='function')
async def guillotina(test_server, postgres, guillotina_main, loop):
    HARD_CACHE.clear()
    server = await test_server(guillotina_main)
    requester = GuillotinaDBRequester(server=server, loop=loop)
    return requester


@pytest.fixture(scope='function')
async def container_requester(guillotina):
    return ContainerRequesterAsyncContextManager(guillotina)


class CockroachStorageAsyncContextManager(object):
    def __init__(self, request, loop):
        self.loop = loop
        self.request = request
        self.storage = None

    async def __aenter__(self):
        dsn = "postgres://root:@localhost:26257/guillotina?sslmode=disable"
        self.storage = CockroachStorage(
            dsn=dsn, name='db', pool_size=20,
            conn_acquire_timeout=0.1)
        await self.storage.initialize(self.loop)
        return self.storage

    async def __aexit__(self, exc_type, exc, tb):
        await self.storage._read_conn.execute("DROP TABLE IF EXISTS objects;")
        await self.storage._read_conn.execute("DROP TABLE IF EXISTS blobs;")
        await self.storage.create()
        await self.storage.finalize()


@pytest.fixture(scope='function')
async def cockroach_storage(postgres, dummy_request, loop):
    return CockroachStorageAsyncContextManager(dummy_request, loop)
