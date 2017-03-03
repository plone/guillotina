# -*- coding: utf-8 -*-
from aiohttp.test_utils import make_mocked_request
from guillotina.auth.policy import Interaction
from guillotina.auth.users import ROOT_USER_ID
from guillotina.auth.users import RootUser
from guillotina.browser import View
from guillotina.content import load_cached_schema
from guillotina.content import Resource
from guillotina.directives import index
from guillotina.directives import metadata
from guillotina.factory import make_app
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDefaultLayer
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.jsonfield import JSONField
from zope.component import getUtility
from zope.interface import implementer
from zope.schema import List

import asyncio
import base64
import guillotina.patch  # noqa
import json
import requests
import time
import unittest


TESTING_PORT = 55001

TESTING_SETTINGS = {
    "databases": [
        {
            "guillotina": {
                "storage": "DEMO",
                "name": "zodbdemo"
            }
        },
    ],
    "port": TESTING_PORT,
    "static": [
        {"favicon.ico": "static/favicon.ico"}
    ],
    "creator": {
        "admin": "admin",
        "password": "admin"
    },
    "cors": {
        "allow_origin": ["*"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660
    },
    "root_user": {
        "password": "admin"
    },
    "utilities": []
}

QUEUE_UTILITY_CONFIG = {
    "provides": "guillotina.async.IQueueUtility",
    "factory": "guillotina.async.QueueUtility",
    "settings": {}
}


ADMIN_TOKEN = base64.b64encode(
    '{}:{}'.format(ROOT_USER_ID, TESTING_SETTINGS['root_user']['password']).encode(
        'utf-8')).decode('utf-8')
DEBUG = False

TERM_SCHEMA = json.dumps({
    'type': 'object',
    'properties': {
        'label': {'type': 'string'},
        'number': {'type': 'number'}
    },
})


class IExample(IResource):

    metadata('categories')

    index('categories', type='nested')
    categories = List(
        title='categories',
        default=[],
        value_type=JSONField(
            title='term',
            schema=TERM_SCHEMA)
    )


@implementer(IExample)
class Example(Resource):
    pass


class MockView(View):

    def __init__(self, context, conn, func):
        self.context = context
        self.request = make_mocked_request('POST', '/')
        self.request.conn = conn
        self.request._db_write_enabled = True
        self.func = func

    def __call__(self, *args, **kw):
        self.func(*args, **kw)


class AsyncMockView(View):

    def __init__(self, context, conn, func, app):
        self.context = context
        self.request = make_mocked_request('POST', '/')
        self.request.conn = conn
        self.request.application = app
        self.request._db_id = 'guillotina'
        self.request._db_write_enabled = True
        self.func = func

    async def __call__(self, *args, **kw):
        await self.func(*args, **kw)


class GuillotinaRequester(object):

    def __init__(self, uri):
        self.uri = uri

    def __call__(
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
        operation = getattr(requests, method.lower(), None)
        if operation:
            resp = operation(self.uri + path, **settings)
            return resp
        return None


class GuillotinaServerBaseLayer(object):
    """Base Layer with the app for unittesting."""

    @classmethod
    def setUp(cls):
        # load test configuration
        from guillotina import test_package  # noqa
        # Aio HTTP app
        cls.aioapp = make_app(settings=TESTING_SETTINGS)
        # Guillotina App Object
        cls.app = getUtility(IApplication, name='root')
        cls.db = cls.app['guillotina']
        cls.app.app.config.execute_actions()
        load_cached_schema()

    @classmethod
    def tearDown(cls):
        del cls.app
        del cls.aioapp


class GuillotinaQueueLayer(GuillotinaServerBaseLayer):

    @classmethod
    def setUp(cls):
        cls.app.add_async_utility(QUEUE_UTILITY_CONFIG)
        loop = cls.aioapp.loop

        import threading

        def loop_in_thread(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        cls.t = threading.Thread(target=loop_in_thread, args=(loop,))
        cls.t.start()

    @classmethod
    def tearDown(cls):
        loop = cls.aioapp.loop

        loop.call_soon_threadsafe(loop.stop)
        while(loop.is_running()):
            time.sleep(1)
        cls.app.del_async_utility(QUEUE_UTILITY_CONFIG)


class GuillotinaBaseLayer(GuillotinaServerBaseLayer):
    """We have a Guillotina Site with asyncio loop"""

    @classmethod
    def setUp(cls):
        """With a Guillotina Site."""
        loop = cls.aioapp.loop
        cls.handler = cls.aioapp.make_handler(debug=DEBUG, keep_alive_on=False)
        cls.srv = loop.run_until_complete(loop.create_server(
            cls.handler,
            '127.0.0.1',
            TESTING_PORT))
        print("Started Testing server on port {port}".format(
            port=TESTING_PORT))

        import threading

        def loop_in_thread(loop):
            asyncio.set_event_loop(loop)
            loop.run_forever()

        cls.t = threading.Thread(target=loop_in_thread, args=(loop,))
        cls.t.start()
        cls.requester = GuillotinaRequester('http://localhost:' + str(TESTING_PORT))
        cls.time = time.time()

    @classmethod
    def tearDown(cls):
        try:
            del cls.requester
        except AttributeError:
            pass

        loop = cls.aioapp.loop

        loop.call_soon_threadsafe(loop.stop)
        while(loop.is_running()):
            time.sleep(1)
        # Wait to stop
        loop.run_until_complete(cls.handler.finish_connections())
        loop.run_until_complete(cls.aioapp.finish())
        cls.srv.close()
        loop.run_until_complete(cls.srv.wait_closed())

    @classmethod
    def testSetUp(cls):
        resp = cls.requester('POST', '/guillotina/', data=json.dumps({
            "@type": "Site",
            "title": "Guillotina Site",
            "id": "guillotina",
            "description": "Description Guillotina Site"
        }))
        assert resp.status_code == 200
        cls.portal = cls.app['guillotina']['guillotina']
        cls.active_connections = []

    @classmethod
    def testTearDown(cls):
        # Restore the copy of the DB
        for conn in cls.active_connections:
            conn.close()
        try:
            resp = cls.requester('DELETE', '/guillotina/guillotina/')
        except requests.exceptions.ConnectionError:
            pass

        assert resp.status_code == 200

    @classmethod
    def new_root(cls):
        conn = cls.app._dbs['guillotina'].open()
        cls.active_connections.append(conn)
        return conn.root()


@implementer(IRequest, IDefaultLayer)
class FakeRequest(object):

    def __init__(self):
        self.security = Interaction(self)
        self.headers = {}


class TestParticipation(object):

    def __init__(self, request):
        self.principal = RootUser('foobar')
        self.interaction = None


class GuillotinaBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.request = FakeRequest()

    def login(self):
        self.request.security.add(TestParticipation(self.request))
        self.request.security.invalidate_cache()
        self.request._cache_groups = {}


class GuillotinaServerBaseTestCase(GuillotinaBaseTestCase):
    """ Only the app created """
    layer = GuillotinaServerBaseLayer


class GuillotinaQueueServerTestCase(GuillotinaBaseTestCase):
    """ Adding the Queue utility """
    layer = GuillotinaQueueLayer


class GuillotinaFunctionalTestCase(GuillotinaBaseTestCase):
    """ With Site and Requester utility """
    layer = GuillotinaBaseLayer
