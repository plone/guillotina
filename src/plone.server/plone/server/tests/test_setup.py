from plone.server.auth.oauth import IOAuth
from zope.component import getUtility
from zope.component.testlayer import LayerBase
from zope.component.testlayer import ZCMLFileLayer

import plone.server
import unittest
import zope.component


ZCMLLayer = ZCMLFileLayer(plone.server, 'configure.zcml')


class ZopeComponentLayer(LayerBase):
    pass


class LayersLayer(object):
    __name__ = 'Layer'
    __bases__ = (
        ZopeComponentLayer(zope.component),
        ZCMLLayer
    )


class TestTraversal(unittest.TestCase):
    layer = LayersLayer()

    def test_auth_registered(self):
        self.assertTrue(getUtility(IOAuth) is not None)
