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
from zope.interface.interface import InterfaceClass

import unittest


def _makeSchema():
    from zope.interface import Interface
    from guillotina.schema import Bytes

    return InterfaceClass(
        "ISchemaTest",
        (Interface,),
        {
            "title": Bytes(title="Title", description="Title", default=b"", required=True),
            "description": Bytes(title="Description", description="Description", default=b"", required=True),
            "spam": Bytes(title="Spam", description="Spam", default=b"", required=True),
        },
        "",
        "guillotina.schema.tests.test_schema",
    )


def _makeDerivedSchema(base=None):
    from guillotina.schema import Bytes

    if base is None:
        base = _makeSchema()

    return InterfaceClass(
        "ISchemaTestSubclass",
        (base,),
        {"foo": Bytes(title="Foo", description="Fooness", default=b"", required=False)},
        "",
        "guillotina.schema.tests.test_schema",
    )


class Test_get_fields(unittest.TestCase):
    def _callFUT(self, schema):
        from guillotina.schema import get_fields

        return get_fields(schema)

    def test_simple(self):
        fields = self._callFUT(_makeSchema())

        self.assertTrue("title" in fields)
        self.assertTrue("description" in fields)
        self.assertTrue("spam" in fields)

        # test whether getName() has the right value
        for key, value in fields.items():
            self.assertEqual(key, value.getName())

    def test_derived(self):
        fields = self._callFUT(_makeDerivedSchema())

        self.assertTrue("title" in fields)
        self.assertTrue("description" in fields)
        self.assertTrue("spam" in fields)
        self.assertTrue("foo" in fields)

        # test whether getName() has the right value
        for key, value in fields.items():
            self.assertEqual(key, value.getName())


class Test_get_fields_in_order(unittest.TestCase):
    def _callFUT(self, schema):
        from guillotina.schema import get_fields_in_order

        return get_fields_in_order(schema)

    def test_simple(self):
        fields = self._callFUT(_makeSchema())
        field_names = [name for name, field in fields]
        self.assertEqual(field_names, ["title", "description", "spam"])
        for key, value in fields:
            self.assertEqual(key, value.getName())

    def test_derived(self):
        fields = self._callFUT(_makeDerivedSchema())
        field_names = [name for name, field in fields]
        self.assertEqual(field_names, ["title", "description", "spam", "foo"])
        for key, value in fields:
            self.assertEqual(key, value.getName())


class Test_getFieldNames(unittest.TestCase):
    def _callFUT(self, schema):
        from guillotina.schema import getFieldNames

        return getFieldNames(schema)

    def test_simple(self):
        names = self._callFUT(_makeSchema())
        self.assertEqual(len(names), 3)
        self.assertTrue("title" in names)
        self.assertTrue("description" in names)
        self.assertTrue("spam" in names)

    def test_derived(self):
        names = self._callFUT(_makeDerivedSchema())
        self.assertEqual(len(names), 4)
        self.assertTrue("title" in names)
        self.assertTrue("description" in names)
        self.assertTrue("spam" in names)
        self.assertTrue("foo" in names)


class Test_getFieldNamesInOrder(unittest.TestCase):
    def _callFUT(self, schema):
        from guillotina.schema import getFieldNamesInOrder

        return getFieldNamesInOrder(schema)

    def test_simple(self):
        names = self._callFUT(_makeSchema())
        self.assertEqual(names, ["title", "description", "spam"])

    def test_derived(self):
        names = self._callFUT(_makeDerivedSchema())
        self.assertEqual(names, ["title", "description", "spam", "foo"])


class Test_getValidationErrors(unittest.TestCase):
    def _callFUT(self, schema, object):
        from guillotina.schema import getValidationErrors

        return getValidationErrors(schema, object)

    def test_schema(self):
        from zope.interface import Interface

        class IEmpty(Interface):
            pass

        errors = self._callFUT(IEmpty, object())
        self.assertEqual(len(errors), 0)

    def test_schema_with_field_errors(self):
        from zope.interface import Interface
        from guillotina.schema import Text
        from guillotina.schema.exceptions import SchemaNotFullyImplemented

        class IWithRequired(Interface):
            must = Text(required=True)

        errors = self._callFUT(IWithRequired, object())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], "must")
        self.assertEqual(errors[0][1].__class__, SchemaNotFullyImplemented)

    def test_schema_with_invariant_errors(self):
        from zope.interface import Interface
        from zope.interface import invariant
        from zope.interface.exceptions import Invalid

        class IWithFailingInvariant(Interface):
            @invariant
            def _epic_fail(obj):
                raise Invalid("testing")

        errors = self._callFUT(IWithFailingInvariant, object())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], None)
        self.assertEqual(errors[0][1].__class__, Invalid)

    def test_schema_with_invariant_ok(self):
        from zope.interface import Interface
        from zope.interface import invariant

        class IWithPassingInvariant(Interface):
            @invariant
            def _hall_pass(obj):
                pass

        errors = self._callFUT(IWithPassingInvariant, object())
        self.assertEqual(len(errors), 0)


class Test_getSchemaValidationErrors(unittest.TestCase):
    def _callFUT(self, schema, object):
        from guillotina.schema import getSchemaValidationErrors

        return getSchemaValidationErrors(schema, object)

    def test_schema_wo_fields(self):
        from zope.interface import Interface
        from zope.interface import Attribute

        class INoFields(Interface):
            def method():
                pass

            attr = Attribute("ignoreme")

        errors = self._callFUT(INoFields, object())
        self.assertEqual(len(errors), 0)

    def test_schema_with_fields_ok(self):
        from zope.interface import Interface
        from guillotina.schema import Text

        class IWithFields(Interface):
            foo = Text()
            bar = Text()

        class Obj(object):
            foo = "Foo"
            bar = "Bar"

        errors = self._callFUT(IWithFields, Obj())
        self.assertEqual(len(errors), 0)

    def test_schema_with_missing_field(self):
        from zope.interface import Interface
        from guillotina.schema import Text
        from guillotina.schema.exceptions import SchemaNotFullyImplemented

        class IWithRequired(Interface):
            must = Text(required=True)

        errors = self._callFUT(IWithRequired, object())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], "must")
        self.assertEqual(errors[0][1].__class__, SchemaNotFullyImplemented)

    def test_schema_with_invalid_field(self):
        from zope.interface import Interface
        from guillotina.schema import Int
        from guillotina.schema.exceptions import TooSmall

        class IWithMinium(Interface):
            value = Int(required=True, min=0)

        class Obj(object):
            value = -1

        errors = self._callFUT(IWithMinium, Obj())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0][0], "value")
        self.assertEqual(errors[0][1].__class__, TooSmall)


def test_suite():
    return unittest.TestSuite(
        (
            unittest.makeSuite(Test_get_fields),
            unittest.makeSuite(Test_get_fields_in_order),
            unittest.makeSuite(Test_getFieldNames),
            unittest.makeSuite(Test_getFieldNamesInOrder),
            unittest.makeSuite(Test_getValidationErrors),
            unittest.makeSuite(Test_getSchemaValidationErrors),
        )
    )
