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
# flake8: noqa
import unittest


class StateSelectionTest(unittest.TestCase):

    def setUp(self):
        from guillotina.schema.vocabulary import _clear
        from guillotina.schema.vocabulary import getVocabularyRegistry
        from guillotina.schema.tests.states import StateVocabulary
        _clear()
        vr = getVocabularyRegistry()
        vr.register("states", StateVocabulary)

    def tearDown(self):
        from guillotina.schema.vocabulary import _clear
        _clear()

    def _makeSchema(self):
        from zope.interface import Interface
        from guillotina.schema import Choice
        from guillotina.schema.tests.states import StateVocabulary

        class IBirthInfo(Interface):
            state1 = Choice(
                title='State of Birth',
                description='The state in which you were born.',
                vocabulary="states",
                default="AL",
                )
            state2 = Choice(
                title='State of Birth',
                description='The state in which you were born.',
                vocabulary="states",
                default="AL",
                )
            state3 = Choice(
                title='Favorite State',
                description='The state you like the most.',
                vocabulary=StateVocabulary(),
                )
            state4 = Choice(
                title="Name",
                description="The name of your new state",
                vocabulary="states",
                )
        return IBirthInfo

    def test_default_presentation(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IVocabulary
        schema = self._makeSchema()
        field = schema.getDescriptionFor("state1")
        bound = field.bind(object())
        self.assertTrue(verifyObject(IVocabulary, bound.vocabulary))
        self.assertEqual(bound.vocabulary.getTerm("VA").title, "Virginia")

    def test_contains(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IVocabulary
        from guillotina.schema.tests.states import StateVocabulary
        vocab = StateVocabulary()
        self.assertTrue(verifyObject(IVocabulary, vocab))
        count = 0
        L = list(vocab)
        for term in L:
            count += 1
            self.assertTrue(term.value in vocab)
        self.assertEqual(count, len(vocab))
        # make sure we get the same values the second time around:
        L = [term.value for term in L]
        L.sort()
        L2 = [term.value for term in vocab]
        L2.sort()
        self.assertEqual(L, L2)

    def test_prebound_vocabulary(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IVocabulary
        schema = self._makeSchema()
        field = schema.getDescriptionFor("state3")  # type: ignore
        bound = field.bind(None)
        self.assertTrue(bound.vocabularyName is None)
        self.assertTrue(verifyObject(IVocabulary, bound.vocabulary))
        self.assertTrue("AL" in bound.vocabulary)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(StateSelectionTest),
    ))
