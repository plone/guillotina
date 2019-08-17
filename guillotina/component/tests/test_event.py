##############################################################################
#
# Copyright (c) 2012 Zope Foundation and Contributors.
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
import unittest


class Test_dispatch(unittest.TestCase):
    def test_it(self):
        from zope.interface import Interface
        from guillotina.component.globalregistry import get_global_components
        from guillotina.component.event import dispatch

        _adapted = []

        def _adapter(context):
            _adapted.append(context)
            return object()

        gsm = get_global_components()
        gsm.registerHandler(_adapter, (Interface,))
        del _adapted[:]  # clear handler reg
        event = object()
        dispatch(event)
        self.assertEqual(_adapted, [event])


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(Test_dispatch),))
