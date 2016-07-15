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

ZCMLLayer = testlayer.ZCMLFileLayer(plone.server, 'configure.zcml')


class ZopeComponentLayer(testlayer.LayerBase):
    pass


TESTING_PORT = 55001

TESTING_SETTINGS = {
    "databases": [
        {
        "plone": {
            "storage": "DEMO",
            "name": "zodbdemo"
            }
        }
    ],
    "address": TESTING_PORT,
    "static": [
        {"favicon.ico": "static/favicon.ico"}
    ],
    "creator": {
        "admin": "admin",
        "password": "w8E943wOE1Efo4wbvYMOsyK9YGGKoIb69N/2t6Ou2P0="
    },
    "salt": "Y+eYNG9cSQjbtw7ba/eBWg==",
    "utilities": []
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

ADMIN_TOKEN = 'admin'
DEBUG = False


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
            settings['headers']['AUTHORIZATION'] = 'bearer %s' % token

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

    @classmethod
    def testSetUp(cls):
        print("test setup Plone Server Base Layer")

    @classmethod
    def testTearDown(cls):
        print("test teardown Plone Server Base Layer")


class PloneOAuthLayer(PloneServerBaseLayer):

    @classmethod
    def setUp(cls):
        cls.app.add_async_utility(OAUTH_UTILITY_CONFIG)

    @classmethod
    def tearDown(cls):
        cls.app.del_async_utility(OAUTH_UTILITY_CONFIG)


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
            loop.run_forever()

        cls.fut = asyncio.Future(loop=loop)
        cls.t = threading.Thread(target=loop_in_thread, args=(loop,))
        cls.t.start()

    @classmethod
    def tearDown(cls):
        loop = cls.aioapp.loop

        loop.call_soon_threadsafe(loop.stop)
        while(loop.is_running()):
            time.sleep(1)
        # Wait to stop
        loop.run_until_complete(cls.handler.finish_connections())
        loop.run_until_complete(cls.aioapp.finish())
        cls.srv.close()
        loop.run_until_complete(cls.srv.wait_closed())

class RequesterPloneServerLayer(PloneBaseLayer):

    @classmethod
    def setUp(cls):
        """With a Plone Site."""
        cls.requester = PloneRequester('http://localhost:' + str(TESTING_PORT))

    @classmethod
    def tearDown(cls):
        del cls.requester

class PloneServerBaseTestCase(unittest.TestCase):
    """ Only the app created """
    layer = PloneServerBaseLayer


class PloneOAuthServerTestCase(unittest.TestCase):
    """ Adding the OAuth utility """
    layer = PloneOAuthLayer


class PloneServerTestCase(unittest.TestCase):
    """ With a plone site and the asyncio loop """
    layer = PloneBaseLayer


class PloneFunctionalTestCase(unittest.TestCase):
    """ With requester utility """
    layer = RequesterPloneServerLayer