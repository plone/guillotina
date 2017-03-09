##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
# flake8: noqa

# HACK to make sure basicmost event subscriber is installed
import guillotina.component.event

# we really don't need special setup now:
try:
    from zope.testing.cleanup import CleanUp as PlacelessSetup
except ImportError:
    class PlacelessSetup(object):
        def cleanUp(self):
            from guillotina.component.globalregistry import base
            base.__init__('base')
        def setUp(self):
            self.cleanUp()
        def tearDown(self):
            self.cleanUp()

def setUp(test=None):
    PlacelessSetup().setUp()

def tearDown(test=None):
    PlacelessSetup().tearDown()
