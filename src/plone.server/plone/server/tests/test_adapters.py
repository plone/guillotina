# -*- coding: utf-8 -*-
from plone.server.security import Interaction
from plone.server.testing import PloneFunctionalTestCase
from zope.component import getAdapter
from plone.server.factory import RootSpecialPermissions
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.security.interfaces import IInteraction


class TestAdapters(PloneFunctionalTestCase):
    """
    mostly to test adapter registrations
    """

    def test_get_current_interaction(self):
        adapter = getAdapter(self.request, interface=IInteraction)
        self.assertTrue(isinstance(adapter, Interaction))

    def test_RootSpecialPermissions_IDatabase(self):
        root = self.layer.new_root()
        adapter = getAdapter(root, interface=IPrincipalPermissionManager)
        self.assertTrue(isinstance(adapter, RootSpecialPermissions))

    def test_RootSpecialPermissions_IApplication(self):
        adapter = getAdapter(self.layer.app, interface=IPrincipalPermissionManager)
        self.assertTrue(isinstance(adapter, RootSpecialPermissions))
