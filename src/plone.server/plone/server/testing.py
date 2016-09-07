# -*- coding: utf-8 -*-
from zope.component import testlayer

import plone.server
from plone.server.factory import make_app
import zope.component
import unittest
from gocept.pytestlayer.testing import log_to_terminal
from zope.component import getUtility
from plone.server.factory import IApplication
import aiohttp
import pytest
import asyncio
import requests
import time
from plone.dexterity.utils import createContent
from plone.server.browser import View
from aiohttp.test_utils import make_mocked_request
from plone.server.transactions import sync
import json


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
    "utilities": []
}

QUEUE_UTILITY_CONFIG = {
    "provides": "plone.server.async.IQueueUtility",
    "factory": "plone.server.async.QueueUtility",
    "settings": {}
}


OAUTH_UTILITY_CONFIG = {
    "provides": "plone.server.auth.oauth.IOAuth",
    "factory": "plone.server.auth.oauth.OAuth",
    "settings": {
        "server": "http://localhost/",
        "jwt_secret": "secret",
        "jwt_algorithm": "HS256",
        "client_id": 11,
        "client_password": "secret"
    }
}

ADMIN_TOKEN = 'YWRtaW4='
DEBUG = False


class MockView(View):

    def __init__(self, context, conn, func):
        self.context = context
        self.request = make_mocked_request('POST', '/')
        self.request.conn = conn
        self.func = func

    def __call__(self, *args, **kw):
        self.func(*args, **kw)


class AsyncMockView(View):

    def __init__(self, context, conn, func):
        self.context = context
        self.request = make_mocked_request('POST', '/')
        self.request.conn = conn
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

    @classmethod
    def tearDown(cls):
        del cls.app
        del cls.aioapp


class PloneOAuthLayer(PloneServerBaseLayer):

    @classmethod
    def setUp(cls):
        cls.app.add_async_utility(OAUTH_UTILITY_CONFIG)

    @classmethod
    def tearDown(cls):
        cls.app.del_async_utility(OAUTH_UTILITY_CONFIG)


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
        resp = cls.requester('POST', '/plone/', data=json.dumps({
            "@type": "Plone Site",
            "title": "Plone Site",
            "id": "plone",
            "description": "Description Plone Site"
        }))
        assert resp.status_code == 200
        from copy import deepcopy
        cls.site = deepcopy(cls.app['plone']['plone'])

    @classmethod
    def tearDown(cls):
        cls.requester('DELETE', '/plone/plone/')
        del cls.requester
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
    def testTearDown(cls):
        # Restore the copy of the DB
        def restore():
            from copy import deepcopy
            cls.app['plone']['plone'] = deepcopy(cls.site)
        mock = MockView(cls.app['plone'], cls.app['plone'].conn, restore)
        mock()


class PloneServerBaseTestCase(unittest.TestCase):
    """ Only the app created """
    layer = PloneServerBaseLayer


class PloneOAuthServerTestCase(unittest.TestCase):
    """ Adding the OAuth utility """
    layer = PloneOAuthLayer


class PloneQueueServerTestCase(unittest.TestCase):
    """ Adding the OAuth utility """
    layer = PloneQueueLayer


class PloneFunctionalTestCase(unittest.TestCase):
    """ With Site and Requester utility """
    layer = PloneBaseLayer