# -*- coding: utf-8 -*-
from guillotina.testing import GuillotinaServerBaseTestCase
from guillotina.traversal import TraversalRouter


class TestServer(GuillotinaServerBaseTestCase):

    def test_make_app(self):
        self.assertTrue(self.layer.aioapp is not None)
        self.assertEqual(type(self.layer.aioapp.router), TraversalRouter)
        self.assertEqual(self.layer.aioapp, self.layer.app.app)
