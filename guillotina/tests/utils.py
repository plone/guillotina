from aiohttp.test_utils import make_mocked_request
from guillotina.auth.users import RootUser
from guillotina.behaviors import apply_markers
from guillotina.content import Item
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.security.policy import Interaction
from time import sleep
from zope.interface import alsoProvides
from zope.interface import implementer

import json
import os
import uuid


def get_mocked_request(db=None):
    request = make_mocked_request('POST', '/')
    request.interaction = None
    alsoProvides(request, IRequest)
    alsoProvides(request, IDefaultLayer)
    if db is not None:
        db._db.request = request
        request._db_id = db.id
        request._db = db
        request._tm = db.new_transaction_manager()
        request._tm.request = request  # so get_current_request can find it...
    return request


def login(request):
    request.security = Interaction(request)
    request.security.add(TestParticipation(request))
    request.security.invalidate_cache()
    request._cache_groups = {}


async def get_root(request):
    await request._tm.begin(request=request)
    root = await request._tm.root()
    return root


async def get_container(requester=None, request=None):
    if request is None:
        request = get_mocked_request(requester.db)
    root = await get_root(request)
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


POSTGRESQL_IMAGE = 'postgres:9.6'


def run_docker_postgresql(label='testingaiopg'):
    import docker
    docker_client = docker.from_env(version='1.23')

    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': label})
    for test_container in test_containers:
        test_container.stop()
        test_container.remove(v=True, force=True)

    # Create a new one
    container = docker_client.containers.run(
        image=POSTGRESQL_IMAGE,
        labels=[label],
        detach=True,
        ports={
            '5432/tcp': 5432
        },
        cap_add=['IPC_LOCK'],
        mem_limit='1g',
        environment={
            'POSTGRES_PASSWORD': '',
            'POSTGRES_DB': 'guillotina',
            'POSTGRES_USER': 'postgres'
        },
        privileged=True
    )
    ident = container.id
    count = 1

    container_obj = docker_client.containers.get(ident)

    opened = False
    host = ''

    print('starting postgresql')
    while count < 30 and not opened:
        count += 1
        try:
            container_obj = docker_client.containers.get(ident)
        except docker.errors.NotFound:
            continue
        sleep(1)
        if container_obj.attrs['NetworkSettings']['IPAddress'] != '':
            if os.environ.get('TESTING', '') == 'jenkins':
                host = container_obj.attrs['NetworkSettings']['IPAddress']
            else:
                host = 'localhost'

        if host != '':
            try:
                conn = psycopg2.connect("dbname=guillotina user=postgres host=%s port=5432" % host)  # noqa
                cur = conn.cursor()
                cur.execute("SELECT 1;")
                cur.fetchone()
                cur.close()
                conn.close()
                opened = True
            except: # noqa
                conn = None
                cur = None
    print('postgresql started')
    return host


def cleanup_postgres_docker(label='testingaiopg'):
    import docker
    docker_client = docker.from_env(version='1.23')
    # Clean up possible other docker containers
    test_containers = docker_client.containers.list(
        all=True,
        filters={'label': label})
    for test_container in test_containers:
        test_container.kill()
        test_container.remove(v=True, force=True)


class ContainerRequesterAsyncContextManager(object):
    def __init__(self, guillotina):
        self.guillotina = guillotina
        self.requester = None

    async def get_requester(self):
        return await self.guillotina

    async def __aenter__(self):
        requester = await self.get_requester()
        resp, status = await requester('POST', '/db', data=json.dumps({
            "@type": "Container",
            "title": "Guillotina Container",
            "id": "guillotina",
            "description": "Description Guillotina Container"
        }))
        assert status == 200
        self.requester = requester
        return requester

    async def __aexit__(self, exc_type, exc, tb):
        resp, status = await self.requester('DELETE', '/db/guillotina')
        assert status == 200


def create_content(factory=Item, type_name='Item', id='foobar'):
    obj = factory()
    obj.type_name = type_name
    obj._p_oid = uuid.uuid4().hex
    obj.__name__ = obj.id = id
    apply_markers(obj, None)
    return obj
