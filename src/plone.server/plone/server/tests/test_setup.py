# -*- coding: utf-8 -*-
from plone.server.auth.oauth import IOAuth
from plone.server.testing import PloneOAuthServerTestCase
from zope.component import getUtility


class TestTraversal(PloneOAuthServerTestCase):

    def test_auth_registered(self):
        self.assertTrue(getUtility(IOAuth) is not None)
