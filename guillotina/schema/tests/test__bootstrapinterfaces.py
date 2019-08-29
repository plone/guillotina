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


class ValidationErrorTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema.exceptions import ValidationError

        return ValidationError

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_doc(self):
        class Derived(self._getTargetClass()):
            """DERIVED"""

        inst = Derived()
        self.assertEqual(inst.doc(), "DERIVED")

    def test___eq___no_args(self):
        ve = self._makeOne()
        self.assertEqual(ve == object(), False)

    def test___eq___w_args(self):
        left = self._makeOne("abc")
        right = self._makeOne("def")
        self.assertEqual(left == right, False)
        self.assertEqual(left == left, True)
        self.assertEqual(right == right, True)


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(ValidationErrorTests),))
