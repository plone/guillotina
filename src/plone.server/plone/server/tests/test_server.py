# -*- coding: utf-8 -*-
from plone.server.testing import PloneServerBaseTestCase
from plone.server.traversal import TraversalRouter

import pytest


class TestServer(PloneServerBaseTestCase):

    @pytest.yield_fixture
    def test_make_app(self):
        self.assertTrue(self.layer.aioapp is not None)
        self.assertEqual(type(self.layer.aioapp.router), TraversalRouter)
        self.assertEqual(self.layer.aioapp, self.layer.app.app)


