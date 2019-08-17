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


class ValidatedPropertyTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import ValidatedProperty

        return ValidatedProperty

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___set___not_missing_w_check(self):
        _checked = []

        def _check(inst, value):
            _checked.append((inst, value))

        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop", _check)

        inst = Test()
        inst.prop = "PROP"
        self.assertEqual(inst._prop, "PROP")
        self.assertEqual(_checked, [(inst, "PROP")])

    def test___set___not_missing_wo_check(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test(ValueError)

        def _provoke(inst):
            inst.prop = "PROP"

        self.assertRaises(ValueError, _provoke, inst)
        self.assertEqual(inst._prop, None)

    def test___set___w_missing_wo_check(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test(ValueError)
        inst.prop = DummyInst.missing_value
        self.assertEqual(inst._prop, DummyInst.missing_value)

    def test___get__(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test()
        inst._prop = "PROP"
        self.assertEqual(inst.prop, "PROP")


class DefaultPropertyTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import DefaultProperty

        return DefaultProperty

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test___get___wo_defaultFactory_miss(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test()
        inst.defaultFactory = None

        def _provoke(inst):
            return inst.prop

        self.assertRaises(KeyError, _provoke, inst)

    def test___get___wo_defaultFactory_hit(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test()
        inst.defaultFactory = None
        inst._prop = "PROP"
        self.assertEqual(inst.prop, "PROP")

    def test__get___wo_defaultFactory_in_dict(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test()
        inst._prop = "PROP"
        self.assertEqual(inst.prop, "PROP")

    def test___get___w_defaultFactory_not_ICAF_no_check(self):
        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop")

        inst = Test(ValueError)

        def _factory():
            return "PROP"

        inst.defaultFactory = _factory

        def _provoke(inst):
            return inst.prop

        self.assertRaises(ValueError, _provoke, inst)

    def test___get___w_defaultFactory_w_ICAF_w_check(self):
        from zope.interface import directlyProvides
        from guillotina.schema._bootstrapinterfaces import IContextAwareDefaultFactory

        _checked = []

        def _check(inst, value):
            _checked.append((inst, value))

        class Test(DummyInst):
            _prop = None
            prop = self._makeOne("_prop", _check)

        inst = Test(ValueError)
        inst.context = object()
        _called_with = []

        def _factory(context):
            _called_with.append(context)
            return "PROP"

        directlyProvides(_factory, IContextAwareDefaultFactory)
        inst.defaultFactory = _factory
        self.assertEqual(inst.prop, "PROP")
        self.assertEqual(_checked, [(inst, "PROP")])
        self.assertEqual(_called_with, [inst.context])


class FieldTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Field

        return Field

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        field = self._makeOne()
        self.assertEqual(field.__name__, "")
        self.assertEqual(field.__doc__, "")
        self.assertEqual(field.title, "")
        self.assertEqual(field.description, "")
        self.assertEqual(field.required, True)
        self.assertEqual(field.readonly, False)
        self.assertEqual(field.constraint(object()), True)
        self.assertEqual(field.default, None)
        self.assertEqual(field.defaultFactory, None)
        self.assertEqual(field.missing_value, None)
        self.assertEqual(field.context, None)

    def test_ctor_w_title_wo_description(self):
        field = self._makeOne("TITLE")
        self.assertEqual(field.__name__, "")
        self.assertEqual(field.__doc__, "TITLE")
        self.assertEqual(field.title, "TITLE")
        self.assertEqual(field.description, "")

    def test_ctor_wo_title_w_description(self):
        field = self._makeOne(description="DESC")
        self.assertEqual(field.__name__, "")
        self.assertEqual(field.__doc__, "DESC")
        self.assertEqual(field.title, "")
        self.assertEqual(field.description, "DESC")

    def test_ctor_w_both_title_and_description(self):
        field = self._makeOne("TITLE", "DESC", "NAME")
        self.assertEqual(field.__name__, "NAME")
        self.assertEqual(field.__doc__, "TITLE\n\nDESC")
        self.assertEqual(field.title, "TITLE")
        self.assertEqual(field.description, "DESC")

    def test_ctor_order_madness(self):
        klass = self._getTargetClass()
        order_before = klass.order
        field = self._makeOne()
        order_after = klass.order
        self.assertEqual(order_after, order_before + 1)
        self.assertEqual(field.order, order_after)

    def test_explicit_required_readonly_missingValue(self):
        obj = object()
        field = self._makeOne(required=False, readonly=True, missing_value=obj)
        self.assertEqual(field.required, False)
        self.assertEqual(field.readonly, True)
        self.assertEqual(field.missing_value, obj)

    def test_explicit_constraint_default(self):
        _called_with = []
        obj = object()

        def _constraint(value):
            _called_with.append(value)
            return value is obj

        field = self._makeOne(required=False, readonly=True, constraint=_constraint, default=obj)
        self.assertEqual(field.required, False)
        self.assertEqual(field.readonly, True)
        self.assertEqual(_called_with, [obj])
        self.assertEqual(field.constraint(self), False)
        self.assertEqual(_called_with, [obj, self])
        self.assertEqual(field.default, obj)

    def test_explicit_defaultFactory(self):
        _called_with = []
        obj = object()

        def _constraint(value):
            _called_with.append(value)
            return value is obj

        def _factory():
            return obj

        field = self._makeOne(required=False, readonly=True, constraint=_constraint, defaultFactory=_factory)
        self.assertEqual(field.required, False)
        self.assertEqual(field.readonly, True)
        self.assertEqual(field.constraint(self), False)
        self.assertEqual(_called_with, [self])
        self.assertEqual(field.default, obj)
        self.assertEqual(_called_with, [self, obj])
        self.assertEqual(field.defaultFactory, _factory)

    def test_explicit_defaultFactory_returning_missing_value(self):
        def _factory():
            return None

        field = self._makeOne(required=True, defaultFactory=_factory)
        self.assertEqual(field.default, None)

    def test_bind(self):
        obj = object()
        field = self._makeOne()
        bound = field.bind(obj)
        self.assertEqual(bound.context, obj)
        expected = dict(field.__dict__)
        found = dict(bound.__dict__)
        found.pop("context")
        self.assertEqual(found, expected)
        self.assertEqual(bound.__class__, field.__class__)

    def test_validate_missing_not_required(self):
        missing = object()

        def _fail(value):
            return False

        field = self._makeOne(required=False, missing_value=missing, constraint=_fail)
        self.assertEqual(field.validate(missing), None)  # doesn't raise

    def test_validate_missing_and_required(self):
        from guillotina.schema.exceptions import RequiredMissing

        missing = object()

        def _fail(value):
            return False

        field = self._makeOne(required=True, missing_value=missing, constraint=_fail)
        self.assertRaises(RequiredMissing, field.validate, missing)

    def test_validate_wrong_type(self):
        from guillotina.schema.exceptions import WrongType

        def _fail(value):
            return False

        field = self._makeOne(required=True, constraint=_fail)
        field._type = str
        self.assertRaises(WrongType, field.validate, 1)

    def test_validate_constraint_fails(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied

        def _fail(value):
            return False

        field = self._makeOne(required=True, constraint=_fail)
        field._type = int
        self.assertRaises(ConstraintNotSatisfied, field.validate, 1)

    def test_validate_constraint_raises_StopValidation(self):
        from guillotina.schema.exceptions import StopValidation

        def _fail(value):
            raise StopValidation

        field = self._makeOne(required=True, constraint=_fail)
        field._type = int
        field.validate(1)  # doesn't raise

    def test___eq___different_type(self):
        left = self._makeOne()

        class Derived(self._getTargetClass()):
            pass

        right = Derived()
        self.assertEqual(left == right, False)
        self.assertEqual(left != right, True)

    def test___eq___same_type_different_attrs(self):
        left = self._makeOne(required=True)
        right = self._makeOne(required=False)
        self.assertEqual(left == right, False)
        self.assertEqual(left != right, True)

    def test___eq___same_type_same_attrs(self):
        left = self._makeOne()
        right = self._makeOne()
        self.assertEqual(left == right, True)
        self.assertEqual(left != right, False)

    def test_get_miss(self):
        field = self._makeOne(__name__="nonesuch")
        inst = DummyInst()
        self.assertRaises(AttributeError, field.get, inst)

    def test_get_hit(self):
        field = self._makeOne(__name__="extant")
        inst = DummyInst()
        inst.extant = "EXTANT"
        self.assertEqual(field.get(inst), "EXTANT")

    def test_query_miss_no_default(self):
        field = self._makeOne(__name__="nonesuch")
        inst = DummyInst()
        self.assertEqual(field.query(inst), None)

    def test_query_miss_w_default(self):
        field = self._makeOne(__name__="nonesuch")
        inst = DummyInst()
        self.assertEqual(field.query(inst, "DEFAULT"), "DEFAULT")

    def test_query_hit(self):
        field = self._makeOne(__name__="extant")
        inst = DummyInst()
        inst.extant = "EXTANT"
        self.assertEqual(field.query(inst), "EXTANT")

    def test_set_readonly(self):
        field = self._makeOne(__name__="lirame", readonly=True)
        inst = DummyInst()
        self.assertRaises(TypeError, field.set, inst, "VALUE")

    def test_set_hit(self):
        field = self._makeOne(__name__="extant")
        inst = DummyInst()
        inst.extant = "BEFORE"
        field.set(inst, "AFTER")
        self.assertEqual(inst.extant, "AFTER")


class ContainerTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Container

        return Container

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing

        field = self._makeOne()
        self.assertRaises(RequiredMissing, field.validate, None)

    def test__validate_not_collection_not_iterable(self):
        from guillotina.schema.exceptions import NotAContainer

        cont = self._makeOne()
        self.assertRaises(NotAContainer, cont._validate, object())

    def test__validate_collection_but_not_iterable(self):
        cont = self._makeOne()

        class Dummy(object):
            def __contains__(self, item):
                return False

        cont._validate(Dummy())  # doesn't raise

    def test__validate_not_collection_but_iterable(self):
        cont = self._makeOne()

        class Dummy(object):
            def __iter__(self):
                return iter(())

        cont._validate(Dummy())  # doesn't raise

    def test__validate_w_collections(self):
        cont = self._makeOne()
        cont._validate(())  # doesn't raise
        cont._validate([])  # doesn't raise
        cont._validate("")  # doesn't raise
        cont._validate({})  # doesn't raise


class IterableTests(ContainerTests):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Iterable

        return Iterable

    def test__validate_collection_but_not_iterable(self):
        from guillotina.schema.exceptions import NotAnIterator

        itr = self._makeOne()

        class Dummy(object):
            def __contains__(self, item):
                return False

        self.assertRaises(NotAnIterator, itr._validate, Dummy())


class OrderableTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Orderable

        return Orderable

    def _makeOne(self, *args, **kw):
        # Orderable is a mixin for a type derived from Field
        from guillotina.schema._bootstrapfields import Field

        class Mixed(self._getTargetClass(), Field):
            pass

        return Mixed(*args, **kw)

    def test_ctor_defaults(self):
        ordb = self._makeOne()
        self.assertEqual(ordb.min, None)
        self.assertEqual(ordb.max, None)
        self.assertEqual(ordb.default, None)

    def test_ctor_default_too_small(self):
        # This test exercises _validate, too
        from guillotina.schema.exceptions import TooSmall

        self.assertRaises(TooSmall, self._makeOne, min=0, default=-1)

    def test_ctor_default_too_large(self):
        # This test exercises _validate, too
        from guillotina.schema.exceptions import TooBig

        self.assertRaises(TooBig, self._makeOne, max=10, default=11)


class MinMaxLenTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import MinMaxLen

        return MinMaxLen

    def _makeOne(self, *args, **kw):
        # MinMaxLen is a mixin for a type derived from Field
        from guillotina.schema._bootstrapfields import Field

        class Mixed(self._getTargetClass(), Field):
            pass

        return Mixed(*args, **kw)

    def test_ctor_defaults(self):
        mml = self._makeOne()
        self.assertEqual(mml.min_length, 0)
        self.assertEqual(mml.max_length, None)

    def test_validate_too_short(self):
        from guillotina.schema.exceptions import TooShort

        mml = self._makeOne(min_length=1)
        self.assertRaises(TooShort, mml._validate, ())

    def test_validate_too_long(self):
        from guillotina.schema.exceptions import TooLong

        mml = self._makeOne(max_length=2)
        self.assertRaises(TooLong, mml._validate, (0, 1, 2))


class TextTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Text

        return Text

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        txt = self._makeOne()
        self.assertEqual(txt._type, str)

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType

        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, b"")
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_w_invalid_default(self):
        from guillotina.schema.exceptions import ValidationError

        self.assertRaises(ValidationError, self._makeOne, default=b"")

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate("")
        field.validate("abc")
        field.validate("abc\ndef")
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing

        field = self._makeOne()
        field.validate("")
        field.validate("abc")
        field.validate("abc\ndef")
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_from_unicode_miss(self):
        from guillotina.schema.exceptions import WrongType

        deadbeef = b"DEADBEEF"
        txt = self._makeOne()
        self.assertRaises(WrongType, txt.from_unicode, deadbeef)

    def test_from_unicode_hit(self):
        deadbeef = "DEADBEEF"
        txt = self._makeOne()
        self.assertEqual(txt.from_unicode(deadbeef), deadbeef)


class TextLineTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._field import TextLine

        return TextLine

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_ITextLine(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import ITextLine

        verifyClass(ITextLine, self._getTargetClass())

    def test_instance_conforms_to_ITextLine(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import ITextLine

        verifyObject(ITextLine, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType

        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, b"")
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate("")
        field.validate("abc")
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing

        field = self._makeOne()
        field.validate("")
        field.validate("abc")
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_constraint(self):
        field = self._makeOne()
        self.assertEqual(field.constraint(""), True)
        self.assertEqual(field.constraint("abc"), True)
        self.assertEqual(field.constraint("abc\ndef"), False)


class PasswordTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Password

        return Password

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_set_unchanged(self):
        klass = self._getTargetClass()
        pw = self._makeOne()
        inst = DummyInst()
        before = dict(inst.__dict__)
        pw.set(inst, klass.UNCHANGED_PASSWORD)  # doesn't raise, doesn't write
        after = dict(inst.__dict__)
        self.assertEqual(after, before)

    def test_set_normal(self):
        pw = self._makeOne(__name__="password")
        inst = DummyInst()
        pw.set(inst, "PASSWORD")
        self.assertEqual(inst.password, "PASSWORD")

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate("")
        field.validate("abc")
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing

        field = self._makeOne()
        field.validate("")
        field.validate("abc")
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_unchanged_not_already_set(self):
        from guillotina.schema.exceptions import WrongType

        klass = self._getTargetClass()
        inst = DummyInst()
        pw = self._makeOne(__name__="password").bind(inst)
        self.assertRaises(WrongType, pw.validate, klass.UNCHANGED_PASSWORD)

    def test_validate_unchanged_already_set(self):
        klass = self._getTargetClass()
        inst = DummyInst()
        inst.password = "foobar"
        pw = self._makeOne(__name__="password").bind(inst)
        pw.validate(klass.UNCHANGED_PASSWORD)  # doesn't raise

    def test_constraint(self):
        field = self._makeOne()
        self.assertEqual(field.constraint(""), True)
        self.assertEqual(field.constraint("abc"), True)
        self.assertEqual(field.constraint("abc\ndef"), False)


class BoolTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Bool

        return Bool

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        txt = self._makeOne()
        self.assertEqual(txt._type, bool)

    def test__validate_w_int(self):
        boo = self._makeOne()
        boo._validate(0)  # doesn't raise
        boo._validate(1)  # doesn't raise

    def test_set_w_int(self):
        boo = self._makeOne(__name__="boo")
        inst = DummyInst()
        boo.set(inst, 0)
        self.assertEqual(inst.boo, False)
        boo.set(inst, 1)
        self.assertEqual(inst.boo, True)

    def test_from_unicode_miss(self):
        txt = self._makeOne()
        self.assertEqual(txt.from_unicode(""), False)
        self.assertEqual(txt.from_unicode("0"), False)
        self.assertEqual(txt.from_unicode("1"), False)
        self.assertEqual(txt.from_unicode("False"), False)
        self.assertEqual(txt.from_unicode("false"), False)

    def test_from_unicode_hit(self):
        txt = self._makeOne()
        self.assertEqual(txt.from_unicode("True"), True)
        self.assertEqual(txt.from_unicode("true"), True)


class IntTests(unittest.TestCase):
    def _getTargetClass(self):
        from guillotina.schema._bootstrapfields import Int

        return Int

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        txt = self._makeOne()
        self.assertEqual(txt._type, int)

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(None)
        field.validate(10)
        field.validate(0)
        field.validate(-1)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing

        field = self._makeOne()
        field.validate(10)
        field.validate(0)
        field.validate(-1)
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min(self):
        from guillotina.schema.exceptions import TooSmall

        field = self._makeOne(min=10)
        field.validate(10)
        field.validate(20)
        self.assertRaises(TooSmall, field.validate, 9)
        self.assertRaises(TooSmall, field.validate, -10)

    def test_validate_max(self):
        from guillotina.schema.exceptions import TooBig

        field = self._makeOne(max=10)
        field.validate(5)
        field.validate(9)
        field.validate(10)
        self.assertRaises(TooBig, field.validate, 11)
        self.assertRaises(TooBig, field.validate, 20)

    def test_validate_min_and_max(self):
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall

        field = self._makeOne(min=0, max=10)
        field.validate(0)
        field.validate(5)
        field.validate(10)
        self.assertRaises(TooSmall, field.validate, -10)
        self.assertRaises(TooSmall, field.validate, -1)
        self.assertRaises(TooBig, field.validate, 11)
        self.assertRaises(TooBig, field.validate, 20)

    def test_from_unicode_miss(self):
        txt = self._makeOne()
        self.assertRaises(ValueError, txt.from_unicode, "")
        self.assertRaises(ValueError, txt.from_unicode, "False")
        self.assertRaises(ValueError, txt.from_unicode, "True")

    def test_from_unicode_hit(self):
        txt = self._makeOne()
        self.assertEqual(txt.from_unicode("0"), 0)
        self.assertEqual(txt.from_unicode("1"), 1)
        self.assertEqual(txt.from_unicode("-1"), -1)


class DummyInst(object):
    missing_value = object()

    def __init__(self, exc=None):
        self._exc = exc

    def validate(self, value):
        if self._exc is not None:
            raise self._exc()


def test_suite():
    return unittest.TestSuite(
        (
            unittest.makeSuite(ValidatedPropertyTests),
            unittest.makeSuite(DefaultPropertyTests),
            unittest.makeSuite(FieldTests),
            unittest.makeSuite(ContainerTests),
            unittest.makeSuite(IterableTests),
            unittest.makeSuite(OrderableTests),
            unittest.makeSuite(MinMaxLenTests),
            unittest.makeSuite(TextTests),
            unittest.makeSuite(TextLineTests),
            unittest.makeSuite(PasswordTests),
            unittest.makeSuite(BoolTests),
            unittest.makeSuite(IntTests),
        )
    )
