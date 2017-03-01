# -*- coding: utf-8 -*-
from guillotina.testing import GuillotinaServerBaseTestCase
from guillotina.traversal import TraversalRouter

import pytest


class TestServer(GuillotinaServerBaseTestCase):

    @pytest.yield_fixture
    def test_make_app(self):
        self.assertTrue(self.layer.aioapp is not None)
        self.assertEqual(type(self.layer.aioapp.router), TraversalRouter)
        self.assertEqual(self.layer.aioapp, self.layer.app.app)
