from plone.server.auth.oauth import IOAuth
from zope.component import getUtility
from plone.server.testing import PLONE_LAYER
import unittest


class TestTraversal(unittest.TestCase):
    layer = PLONE_LAYER

    def test_auth_registered(self):
        self.assertTrue(getUtility(IOAuth) is not None)
