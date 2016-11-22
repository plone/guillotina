# -*- coding: utf-8 -*-
import plone.server.patch  # noqa
from aiohttp.test_utils import make_mocked_request
from plone.server.browser import View
from plone.server.factory import IApplication
from plone.server.factory import make_app
from zope.component import getUtility
from zope.configuration.xmlconfig import include
from zope.component import getGlobalSiteManager
from zope.security.interfaces import IInteraction
from plone.server.api.layer import IDefaultLayer
from plone.server.interfaces import IRequest
from zope.interface import implementer
from plone.server.auth.participation import RootParticipation

import asyncio
import json
import requests
import sys
import time
import unittest


TESTING_PORT = 55001

TESTING_SETTINGS = {
    "databases": [
        {
            "plone": {
                "storage": "DEMO",
                "name": "zodbdemo"
            }
        },
    ],
    "address": TESTING_PORT,
    "static": [
        {"favicon.ico": "static/favicon.ico"}
    ],
    "creator": {
        "admin": "admin",
        "password": "YWRtaW4="
    },
    "cors": {
        "allow_origin": ["*"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660
    },
    "utilities": []
}

QUEUE_UTILITY_CONFIG = {
    "provides": "plone.server.async.IQueueUtility",
    "factory": "plone.server.async.QueueUtility",
    "settings": {}
}


ADMIN_TOKEN = 'YWRtaW4='
DEBUG = False


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

    def __init__(self, context, conn, func):
        self.context = context
        self.request = make_mocked_request('POST', '/')
        self.request.conn = conn
        self.request._db_write_enabled = True
        self.func = func

    async def __call__(self, *args, **kw):
        await self.func(*args, **kw)


class PloneRequester(object):

    def __init__(self, uri):
        self.uri = uri

    def __call__(
            self,
            method,
            path,
            params=None,
            data=None,
            authenticated=True,
            token=ADMIN_TOKEN,
            accept='application/json'):

        settings = {}
        settings['headers'] = {}
        if accept is not None:
            settings['headers']['ACCEPT'] = accept
        if authenticated and token is not None:
            settings['headers']['AUTHORIZATION'] = 'Basic %s' % token

        settings['params'] = params
        settings['data'] = data
        operation = getattr(requests, method.lower(), None)
        if operation:
            resp = operation(self.uri + path, **settings)
            return resp
        return None


class PloneServerBaseLayer(object):
    """Base Layer with the app for unittesting."""

    @classmethod
    def setUp(cls):
        # Aio HTTP app
        cls.aioapp = make_app(settings=TESTING_SETTINGS)
        # Plone App Object
        cls.app = getUtility(IApplication, name='root')
        cls.db = cls.app['plone']
        include(cls.app.app.config, 'testing.zcml', sys.modules['plone.server'])
        cls.app.app.config.execute_actions()

    @classmethod
    def tearDown(cls):
        del cls.app
        del cls.aioapp


class PloneQueueLayer(PloneServerBaseLayer):

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


class PloneBaseLayer(PloneServerBaseLayer):
    """We have a Plone Site with asyncio loop"""

    @classmethod
    def setUp(cls):
        """With a Plone Site."""
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
        cls.requester = PloneRequester('http://localhost:' + str(TESTING_PORT))
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
        resp = cls.requester('POST', '/plone/', data=json.dumps({
            "@type": "Site",
            "title": "Plone Site",
            "id": "plone",
            "description": "Description Plone Site"
        }))
        assert resp.status_code in (200, 401)  # 401 is if site already exists...
        cls.portal = cls.app['plone']['plone']
        cls.active_connections = []

    @classmethod
    def testTearDown(cls):
        # Restore the copy of the DB
        for conn in cls.active_connections:
            conn.close()
        try:
            resp = cls.requester('DELETE', '/plone/plone/')
        except requests.exceptions.ConnectionError:
            pass

        assert resp.status_code == 200
        # def restore(conn):
        #     from copy import deepcopy
        #     del conn.root()['plone']['plone']
        #     conn.root()['plone']['plone'] = deepcopy(cls.site)
        # restore_connection = cls.app['plone'].open()
        # mock = MockView(cls.app['plone'], restore_connection, restore)
        # mock()

    @classmethod
    def new_root(cls):
        conn = cls.app._dbs['plone'].open()
        cls.active_connections.append(conn)
        return conn.root()


@implementer(IRequest, IDefaultLayer)
class FakeRequest(object):

    def __init__(self):
        self.site_components = getGlobalSiteManager()
        self.security = IInteraction(self)


class PloneBaseTestCase(unittest.TestCase):

    def setUp(self):
        self.request = FakeRequest()

    def login(self):
        self.request.security.add(RootParticipation(self.request))
        self.request.security.invalidate_cache()
        self.request._cache_groups = {}


class PloneServerBaseTestCase(PloneBaseTestCase):
    """ Only the app created """
    layer = PloneServerBaseLayer


class PloneQueueServerTestCase(PloneBaseTestCase):
    """ Adding the Queue utility """
    layer = PloneQueueLayer


class PloneFunctionalTestCase(PloneBaseTestCase):
    """ With Site and Requester utility """
    layer = PloneBaseLayer
