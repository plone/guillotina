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
import unittest


class FieldEqualityTests(unittest.TestCase):
    def test_equality(self):

        from guillotina.schema import Int  # noqa
        from guillotina.schema import Text  # noqa

        equality = ['Text(title="Foo", description="Bar")', 'Int(title="Foo", description="Bar")']
        for text in equality:
            self.assertEqual(eval(text), eval(text))


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(FieldEqualityTests),))
