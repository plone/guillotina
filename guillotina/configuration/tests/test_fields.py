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
"""Test guillotina.configuration.fields.
"""
import unittest


class _ConformsToIFromUnicode(object):

    def test_class_conforms_to_IFromUnicode(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IFromUnicode
        verifyClass(IFromUnicode, self._getTargetClass())

    def test_instance_conforms_to_IFromUnicode(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IFromUnicode
        verifyObject(IFromUnicode, self._makeOne())


class PythonIdentifierTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import PythonIdentifier
        return PythonIdentifier
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_fromUnicode_empty(self):
        pi = self._makeOne()
        self.assertEqual(pi.fromUnicode(''), '')

    def test_fromUnicode_normal(self):
        pi = self._makeOne()
        self.assertEqual(pi.fromUnicode('normal'), 'normal')

    def test_fromUnicode_strips_ws(self):
        pi = self._makeOne()
        self.assertEqual(pi.fromUnicode('   '), '')
        self.assertEqual(pi.fromUnicode(' normal  '), 'normal')

    def test__validate_miss(self):
        from guillotina.schema import ValidationError
        from guillotina.configuration._compat import u
        pi = self._makeOne()
        self.assertRaises(ValidationError,
                          pi._validate, u('not-an-identifier'))

    def test__validate_hit(self):
        from guillotina.configuration._compat import u
        pi = self._makeOne()
        pi._validate(u('is_an_identifier'))


class GlobalObjectTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import GlobalObject
        return GlobalObject
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test__validate_wo_value_type(self):
        from guillotina.configuration._compat import u
        from guillotina.configuration._compat import b
        go = self._makeOne(value_type=None)
        for value in [0, 0.0, (), [], set(), frozenset(), u(''), b('')]:
            go._validate(value) #noraise

    def test__validate_w_value_type(self):
        from guillotina.schema import Text
        from guillotina.schema.interfaces import WrongType
        from guillotina.configuration._compat import u
        from guillotina.configuration._compat import b
        go = self._makeOne(value_type=Text())
        go.validate(u(''))
        for value in [0, 0.0, (), [], set(), frozenset(), b('')]:
            self.assertRaises(WrongType, go._validate, value)

    def test_fromUnicode_w_star_and_extra_ws(self):
        go = self._makeOne()
        self.assertEqual(go.fromUnicode(' * '), None)

    def test_fromUnicode_w_resolve_fails(self):
        from guillotina.schema import ValidationError
        from guillotina.configuration.config import ConfigurationError
        class Context(object):
            def resolve(self, name):
                self._resolved = name
                raise ConfigurationError()
        go = self._makeOne()
        context = Context()
        bound = go.bind(context)
        self.assertRaises(ValidationError, bound.fromUnicode, 'tried')
        self.assertEqual(context._resolved, 'tried')

    def test_fromUnicode_w_resolve_success(self):
        _target = object()
        class Context(object):
            def resolve(self, name):
                self._resolved = name
                return _target
        go = self._makeOne()
        context = Context()
        bound = go.bind(context)
        found = bound.fromUnicode('tried')
        self.assertTrue(found is _target)
        self.assertEqual(context._resolved, 'tried')

    def test_fromUnicode_w_resolve_but_validation_fails(self):
        from guillotina.schema import Text
        from guillotina.schema import ValidationError
        _target = object()
        class Context(object):
            def resolve(self, name):
                self._resolved = name
                return _target
        go = self._makeOne(value_type=Text())
        context = Context()
        bound = go.bind(context)
        self.assertRaises(ValidationError, bound.fromUnicode, 'tried')
        self.assertEqual(context._resolved, 'tried')


class GlobalInterfaceTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import GlobalInterface
        return GlobalInterface
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor(self):
        from guillotina.schema import InterfaceField
        gi = self._makeOne()
        self.assertTrue(isinstance(gi.value_type, InterfaceField))

class TokensTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import Tokens
        return Tokens
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_fromUnicode_empty(self):
        tok = self._makeOne()
        self.assertEqual(tok.fromUnicode(''), [])

    def test_fromUnicode_strips_ws(self):
        from guillotina.schema import Text
        from guillotina.configuration._compat import u
        tok = self._makeOne(value_type=Text())
        context = object()
        self.assertEqual(tok.fromUnicode(u(' one two three ')),
                         [u('one'), u('two'), u('three')])

    def test_fromUnicode_invalid(self):
        from guillotina.schema import Int
        from guillotina.configuration.interfaces import InvalidToken
        from guillotina.configuration._compat import u
        tok = self._makeOne(value_type=Int(min=0))
        context = object()
        self.assertRaises(InvalidToken,
                          tok.fromUnicode, u(' 1 -1 3 '))


class PathTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import Path
        return Path
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_fromUnicode_absolute(self):
        import os
        path = self._makeOne()
        self.assertEqual(path.fromUnicode('/'), os.path.normpath('/'))

    def test_fromUnicode_relative(self):
        class Context(object):
            def path(self, value):
                self._pathed = value
                return '/hard/coded'
        context = Context()
        path = self._makeOne()
        bound = path.bind(context)
        self.assertEqual(bound.fromUnicode('relative/path'), '/hard/coded')
        self.assertEqual(context._pathed, 'relative/path')


class BoolTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import Bool
        return Bool
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_fromUnicode_w_true_values(self):
        values = ['1', 'true', 'yes', 't', 'y']
        values += [x.upper() for x in values]
        bo = self._makeOne()
        for value in values:
            self.assertEqual(bo.fromUnicode(value), True)

    def test_fromUnicode_w_false_values(self):
        values = ['0', 'false', 'no', 'f', 'n']
        values += [x.upper() for x in values]
        bo = self._makeOne()
        for value in values:
            self.assertEqual(bo.fromUnicode(value), False)

    def test_fromUnicode_w_invalid(self):
        from guillotina.schema import ValidationError
        bo = self._makeOne()
        self.assertRaises(ValidationError, bo.fromUnicode, 'notvalid')


class MessageIDTests(unittest.TestCase, _ConformsToIFromUnicode):

    def _getTargetClass(self):
        from guillotina.configuration.fields import MessageID
        return MessageID
    
    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def _makeContext(self, domain='testing_domain'):
        class Info(object):
            file = 'test_file'
            line = 42
        class Context(object):
            i18n_domain = domain
            def __init__(self):
                self.i18n_strings = {}
                self.info = Info()
        return Context()

    def test_wo_domain(self):
        import warnings
        from guillotina.configuration._compat import u
        mid = self._makeOne()
        context = self._makeContext(None)
        bound = mid.bind(context)
        with warnings.catch_warnings(record=True) as log:
            msgid = bound.fromUnicode(u('testing'))
        self.assertEqual(len(log), 1)
        self.assertTrue(str(log[0].message).startswith(
                            'You did not specify an i18n translation domain'))
        self.assertEqual(msgid, 'testing')
        self.assertEqual(msgid.default, None)
        self.assertEqual(msgid.domain, 'untranslated')
        self.assertEqual(context.i18n_strings,
                         {'untranslated': {'testing': [('test_file', 42)]}})

    def test_w_empty_id(self):
        import warnings
        from guillotina.configuration._compat import u
        mid = self._makeOne()
        context = self._makeContext()
        bound = mid.bind(context)
        with warnings.catch_warnings(record=True) as log:
            msgid = bound.fromUnicode(u('[] testing'))
        self.assertEqual(len(log), 0)
        self.assertEqual(msgid, 'testing')
        self.assertEqual(msgid.default, None)
        self.assertEqual(msgid.domain, 'testing_domain')
        self.assertEqual(context.i18n_strings,
                         {'testing_domain': {'testing': [('test_file', 42)]}})

    def test_w_id_and_default(self):
        import warnings
        from guillotina.configuration._compat import u
        mid = self._makeOne()
        context = self._makeContext()
        bound = mid.bind(context)
        with warnings.catch_warnings(record=True) as log:
            msgid = bound.fromUnicode(u('[testing] default'))
        self.assertEqual(len(log), 0)
        self.assertEqual(msgid, 'testing')
        self.assertEqual(msgid.default, 'default')
        self.assertEqual(msgid.domain, 'testing_domain')
        self.assertEqual(context.i18n_strings,
                         {'testing_domain': {'testing': [('test_file', 42)]}})


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(PythonIdentifierTests),
        unittest.makeSuite(GlobalObjectTests),
        unittest.makeSuite(GlobalInterfaceTests),
        unittest.makeSuite(TokensTests),
        unittest.makeSuite(PathTests),
        unittest.makeSuite(BoolTests),
        unittest.makeSuite(MessageIDTests),
        ))
