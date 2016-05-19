# -*- coding: utf-8 -*-
from plone.server import factory
from plone.server.testing import PLONE_LAYER
from plone.server.traversal import TraversalRouter

import pytest
import unittest


class TestServer(unittest.TestCase):
    layer = PLONE_LAYER

    @pytest.yield_fixture
    def test_make_app(self):
        app = factory.make_app()
        self.assertTrue(app is not None)
        self.assertEquals(type(app.router), TraversalRouter)
