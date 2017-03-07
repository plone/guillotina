# -*- coding: utf-8 -*-
import docker
import os
import psycopg2

from guillotina.testing import TESTING_SETTINGS
from time import sleep
import pytest
import aiohttp
from aiohttp.test_utils import make_mocked_request
import json
from guillotina.factory import make_app
from guillotina.content import load_cached_schema
from guillotina.testing import ADMIN_TOKEN


IMAGE = 'postgres:9.6'
CONTAINERS_FOR_TESTING_LABEL = 'testingaiopg'
DOCKER_PG_SETTINGS = TESTING_SETTINGS.copy()
DOCKER_PG_SETTINGS['applications'] = []
DOCKER_PG_SETTINGS['databases'][0]['guillotina']['storage'] = 'GDB'

DOCKER_PG_SETTINGS['databases'][0]['guillotina']['partition'] = \
    'guillotina.interfaces.IResource'
DOCKER_PG_SETTINGS['databases'][0]['guillotina']['dsn'] = {
    'scheme': 'postgres',
    'dbname': 'guillotina',
    'user': 'guillotina',
    'host': 'localhost',
    'password': 'test',
    'port': 5432
}

DUMMY_SETTINGS = TESTING_SETTINGS.copy()
DUMMY_SETTINGS['applications'] = []
DUMMY_SETTINGS['databases'][0]['guillotina']['storage'] = 'DUMMY'

DUMMY_SETTINGS['databases'][0]['guillotina']['partition'] = \
    'guillotina.interfaces.IResource'
DUMMY_SETTINGS['databases'][0]['guillotina']['dsn'] = {}


@pytest.fixture(scope='session')
def postgres():
    docker_client = docker.from_env(version='1.23')

    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': CONTAINERS_FOR_TESTING_LABEL})
    for test_container in test_containers:
        test_container.stop()
        test_container.remove(v=True, force=True)

    # Create a new one
    container = docker_client.containers.run(
        image=IMAGE,
        labels=[CONTAINERS_FOR_TESTING_LABEL],
        detach=True,
        ports={
            '5432/tcp': 5432
        },
        cap_add=['IPC_LOCK'],
        mem_limit='1g',
        environment={
            'POSTGRES_PASSWORD': 'test',
            'POSTGRES_DB': 'guillotina',
            'POSTGRES_USER': 'guillotina'
        }
    )
    ident = container.id
    count = 1

    container_obj = docker_client.containers.get(ident)

    opened = False
    host = ''

    while count < 30 and not opened:
        count += 1
        container_obj = docker_client.containers.get(ident)
        print(container_obj.status)
        sleep(2)
        if container_obj.attrs['NetworkSettings']['IPAddress'] != '':
            if os.environ.get('TESTING', '') == 'jenkins':
                host = container_obj.attrs['NetworkSettings']['IPAddress']
            else:
                host = 'localhost'

        if host != '':
            try:
                conn = psycopg2.connect("dbname=guillotina user=guillotina password=test host=%s port=5432" % host)
                cur = conn.cursor()
                cur.execute("SELECT 1;")
                cur.fetchone()
                cur.close()
                conn.close()
                opened = True
            except: # noqa
                conn = None
                cur = None

    DOCKER_PG_SETTINGS['databases'][0]['guillotina']['dsn']['host'] = host

    yield host  # provide the fixture value
    print("teardown postgres")

    docker_client = docker.from_env(version='1.23')
    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': CONTAINERS_FOR_TESTING_LABEL})
    for test_container in test_containers:
        test_container.kill()
        test_container.remove(v=True, force=True)


class GuillotinaDBRequester(object):

    def __init__(self, server, loop):
        self.server = server
        self.loop = loop

    async def __call__(
            self,
            method,
            path,
            params=None,
            data=None,
            authenticated=True,
            auth_type='Basic',
            headers={},
            token=ADMIN_TOKEN,
            accept='application/json'):

        settings = {}
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
                except:
                    value = await resp.read()
                    status = resp.status
        return value, status


# MEMORY DB TESTING FIXTURES


@pytest.fixture(scope='function')
def dummy_guillotina(loop):
    aioapp = make_app(settings=DUMMY_SETTINGS, loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()
    return aioapp


@pytest.fixture(scope='function')
def dummy_request(dummy_guillotina):
    from guillotina.interfaces import IApplication
    from zope.component import getUtility
    root = getUtility(IApplication, name='root')
    db = root['guillotina']
    request = make_mocked_request('POST', '/')
    request._db_id = 'guillotina'
    request._tm = db.new_transaction_manager()
    request._tm.request = request  # so get_current_request can find it...
    return request


@pytest.fixture(scope='function')
async def dummy_txn_root(dummy_request):
    txn = await dummy_request._tm.begin(request=dummy_request)
    context = await dummy_request._tm.root()
    yield context
    await txn.abort()

# POSTGRES WITH DOCKER TESTING FIXTURES


@pytest.fixture(scope='function')
def guillotina_main(loop):
    aioapp = make_app(settings=DOCKER_PG_SETTINGS, loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()
    return aioapp


@pytest.fixture(scope='function')
async def guillotina(test_server, postgres, guillotina_main, loop):
    server = await test_server(guillotina_main)
    requester = GuillotinaDBRequester(server=server, loop=loop)
    return requester


@pytest.fixture(scope='function')
@pytest.yield_fixture
async def site(guillotina):
    requester = await guillotina
    resp, status = await requester('POST', '/guillotina', data=json.dumps({
        "@type": "Site",
        "title": "Guillotina Site",
        "id": "guillotina",
        "description": "Description Guillotina Site"
        }))
    assert resp['id'] == 'guillotina'
    assert status == 200
    yield requester
    resp, status = await requester('DELETE', '/guillotina/guillotina')
    assert status == 200
