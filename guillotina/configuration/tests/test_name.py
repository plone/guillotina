##############################################################################
#
# Copyright (c) 20!2 Zope Foundation and Contributors.
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
"""Test guillotina.configuration.name
"""
import unittest


class Test_resolve(unittest.TestCase):

    def _callFUT(self, *args, **kw):
        from guillotina.configuration.name import resolve
        return resolve(*args, **kw)

    def test_top_level_module(self):
        import os
        self.assertTrue(self._callFUT('os') is os)

    def test_nested_module(self):
        import os.path
        self.assertTrue(self._callFUT('os.path') is os.path)

    def test_function_in_module(self):
        import os.path
        self.assertTrue(self._callFUT('os.path.join') is os.path.join)

    def test_importable_but_not_attr_of_parent(self):
        import sys
        import guillotina.configuration.tests as zct
        self.assertFalse('notyet' in zct.__dict__)
        mod = self._callFUT('guillotina.configuration.tests.notyet')
        self.assertTrue(mod is zct.notyet)
        del zct.notyet
        del sys.modules['guillotina.configuration.tests.notyet']

    def test_function_in_module_relative(self):
        import os.path
        self.assertTrue(self._callFUT('.join', 'os.path') is os.path.join)

    def test_class_in_module(self):
        from guillotina.configuration.tests.directives import Complex
        self.assertTrue(
            self._callFUT('guillotina.configuration.tests.directives.Complex')
                    is Complex)

    def test_class_w_same_name_as_module(self):
        from guillotina.configuration.tests.samplepackage.NamedForClass \
            import NamedForClass
        self.assertTrue(
            self._callFUT(
                'guillotina.configuration.tests.samplepackage.NamedForClass+')
                    is NamedForClass)
        self.assertTrue(
            self._callFUT(
                'guillotina.configuration.tests.samplepackage.NamedForClass.')
                    is NamedForClass)

class Test_getNormalizedName(unittest.TestCase):

    def _callFUT(self, *args, **kw):
        from guillotina.configuration.name import getNormalizedName
        return getNormalizedName(*args, **kw)

    def test_no_dots(self):
        self.assertEqual(self._callFUT('os', None), 'os')

    def test_one_dot(self):
        self.assertEqual(self._callFUT('os.path', None), 'os.path')

    def test_two_dots(self):
        self.assertEqual(self._callFUT('os.path.join', None), 'os.path.join')

    def test_relative(self):
        self.assertEqual(self._callFUT('.join', 'os.path'), 'os.path.join')

    def test_repeat_plus(self):
        self.assertEqual(
            self._callFUT('guillotina.configuration.tests.NamedForClass+', None),
            'guillotina.configuration.tests.NamedForClass+')

    def test_repeat_dot(self):
        self.assertEqual(
            self._callFUT('guillotina.configuration.tests.NamedForClass.', None),
            'guillotina.configuration.tests.NamedForClass+')

    def test_repeat_inferred(self):
        self.assertEqual(
            self._callFUT(
                'guillotina.configuration.tests.NamedForClass.NamedForClass', None),
            'guillotina.configuration.tests.NamedForClass+')


class Test_path(unittest.TestCase):

    def _callFUT(self, *args, **kw):
        from guillotina.configuration.name import path
        return path(*args, **kw)

    def test_absolute(self):
        import os
        absolute_path = os.path.abspath('/absolute')
        self.assertEqual(self._callFUT(absolute_path),
                         os.path.normpath(absolute_path))

    def test_relative_bogus_package(self):
        self.assertRaises(ImportError,
                          self._callFUT, '', 'no.such.package.exists')

    def test_relative_empty(self):
        import os
        self.assertEqual(self._callFUT('', 'guillotina.configuration.tests'),
                         os.path.dirname(__file__))

    def test_relative_w_file(self):
        import os
        self.assertEqual(
            self._callFUT('configure.zcml', 'guillotina.configuration.tests'),
            os.path.join(os.path.dirname(__file__), 'configure.zcml'))



def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test_resolve),
        unittest.makeSuite(Test_resolve),
        unittest.makeSuite(Test_path),
    ))
