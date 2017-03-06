##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
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
"""Tests for for guillotina.configuration.docutils
"""
import unittest


class Test_wrap(unittest.TestCase):

    def _callFUT(self, *args, **kw):
        from guillotina.configuration.docutils import wrap
        return wrap(*args, **kw)

    def test_empty(self):
        self.assertEqual(self._callFUT(''), '\n\n')

    def test_only_whitespace(self):
        self.assertEqual(self._callFUT(' \t\n\r'), '\n\n')

    def test_single_paragraphs(self):
        self.assertEqual(
                self._callFUT('abcde fghij klmno pqrst uvwxy', 10, 3),
                '   abcde\n   fghij\n   klmno\n   pqrst\n   uvwxy\n\n')

    def test_multiple_paragraphs(self):
        self.assertEqual(
                self._callFUT('abcde fghij klmno\n\npqrst uvwxy', 10, 3),
                '   abcde\n   fghij\n   klmno\n\n   pqrst\n   uvwxy\n\n')


class Test_makeDocStructures(unittest.TestCase):

    def _callFUT(self, *args, **kw):
        from guillotina.configuration.docutils import makeDocStructures
        return makeDocStructures(*args, **kw)

    def _makeContext(self):
        class _Context(object):
            def __init__(self):
                self._docRegistry = []
        return _Context()

    def test_empty(self):
        context = self._makeContext()
        namespaces, subdirs = self._callFUT(context)
        self.assertEqual(len(namespaces), 0)
        self.assertEqual(len(subdirs), 0)

    def test_wo_parents(self):
        from zope.interface import Interface
        class ISchema(Interface):
            pass
        class IUsedIn(Interface):
            pass
        NS = 'http://namespace.example.com/main'
        NS2 = 'http://namespace.example.com/other'
        def _one():
            pass
        def _two():
            pass
        def _three():
            pass
        context = self._makeContext()
        context._docRegistry.append(
                    ((NS, 'one'), ISchema, IUsedIn, _one, 'ONE', None))
        context._docRegistry.append(
                    ((NS2, 'two'), ISchema, IUsedIn, _two, 'TWO', None))
        context._docRegistry.append(
                    ((NS, 'three'), ISchema, IUsedIn, _three, 'THREE', None))
        namespaces, subdirs = self._callFUT(context)
        self.assertEqual(len(namespaces), 2)
        self.assertEqual(namespaces[NS], {'one': (ISchema, _one, 'ONE'),
                                          'three': (ISchema, _three, 'THREE')})
        self.assertEqual(namespaces[NS2], {'two': (ISchema, _two, 'TWO')})
        self.assertEqual(len(subdirs), 0)

    def test_w_parents(self):
        from zope.interface import Interface
        class ISchema(Interface):
            pass
        class IUsedIn(Interface):
            pass
        PNS = 'http://namespace.example.com/parent'
        NS = 'http://namespace.example.com/main'
        NS2 = 'http://namespace.example.com/other'
        def _one():
            pass
        def _two():
            pass
        def _three():
            pass
        class Parent(object):
            namespace = PNS
            name = 'parent'
        parent1 = Parent()
        parent2 = Parent()
        parent2.name = 'parent2'
        context = self._makeContext()
        context._docRegistry.append(
                    ((NS, 'one'), ISchema, IUsedIn, _one, 'ONE', parent1))
        context._docRegistry.append(
                    ((NS2, 'two'), ISchema, IUsedIn, _two, 'TWO', parent2))
        context._docRegistry.append(
                    ((NS, 'three'), ISchema, IUsedIn, _three, 'THREE', parent1))
        namespaces, subdirs = self._callFUT(context)
        self.assertEqual(len(namespaces), 0)
        self.assertEqual(len(subdirs), 2)
        self.assertEqual(subdirs[(PNS, 'parent')],
                         [(NS, 'one', ISchema, _one, 'ONE'),
                          (NS, 'three', ISchema, _three, 'THREE')])
        self.assertEqual(subdirs[(PNS, 'parent2')],
                         [(NS2, 'two', ISchema, _two, 'TWO')])


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test_wrap),
        unittest.makeSuite(Test_makeDocStructures),
    ))
