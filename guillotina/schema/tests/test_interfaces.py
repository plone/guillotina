# flake8: noqa
import unittest


class Test__is_field(unittest.TestCase):

    def _callFUT(self, value):
        from guillotina.schema.interfaces import _is_field
        return _is_field(value)

    def test_non_fields(self):
        self.assertEqual(self._callFUT(None), False)
        self.assertEqual(self._callFUT(0), False)
        self.assertEqual(self._callFUT(0.0), False)
        self.assertEqual(self._callFUT(True), False)
        self.assertEqual(self._callFUT(b''), False)
        self.assertEqual(self._callFUT(''), False)
        self.assertEqual(self._callFUT(()), False)
        self.assertEqual(self._callFUT([]), False)
        self.assertEqual(self._callFUT({}), False)
        self.assertEqual(self._callFUT(set()), False)
        self.assertEqual(self._callFUT(frozenset()), False)
        self.assertEqual(self._callFUT(object()), False)

    def test_w_normal_fields(self):
        from guillotina.schema import Text
        from guillotina.schema import Bytes
        from guillotina.schema import Int
        from guillotina.schema import Float
        from guillotina.schema import Decimal
        self.assertEqual(self._callFUT(Text()), True)
        self.assertEqual(self._callFUT(Bytes()), True)
        self.assertEqual(self._callFUT(Int()), True)
        self.assertEqual(self._callFUT(Float()), True)
        self.assertEqual(self._callFUT(Decimal()), True)

    def test_w_explicitly_provided(self):
        from zope.interface import directlyProvides
        from guillotina.schema.interfaces import IField

        class Foo(object):
            pass

        foo = Foo()
        self.assertEqual(self._callFUT(foo), False)
        directlyProvides(foo, IField)
        self.assertEqual(self._callFUT(foo), True)


class Test__fields(unittest.TestCase):

    def _callFUT(self, values):
        from guillotina.schema.interfaces import _fields
        return _fields(values)

    def test_empty_containers(self):
        self.assertEqual(self._callFUT(()), True)
        self.assertEqual(self._callFUT([]), True)

    def test_w_non_fields(self):
        self.assertEqual(self._callFUT([None]), False)
        self.assertEqual(self._callFUT(['']), False)
        self.assertEqual(self._callFUT([object()]), False)

    def test_w_fields(self):
        from guillotina.schema import Text
        from guillotina.schema import Bytes
        from guillotina.schema import Int
        from guillotina.schema import Float
        from guillotina.schema import Decimal
        self.assertEqual(self._callFUT([Text()]), True)
        self.assertEqual(self._callFUT([Bytes()]), True)
        self.assertEqual(self._callFUT([Int()]), True)
        self.assertEqual(self._callFUT([Float()]), True)
        self.assertEqual(self._callFUT([Decimal()]), True)
        self.assertEqual(
            self._callFUT([Text(), Bytes(), Int(), Float(), Decimal()]),
            True
        )

    def test_w_mixed(self):
        from guillotina.schema import Text
        from guillotina.schema import Bytes
        from guillotina.schema import Int
        from guillotina.schema import Float
        from guillotina.schema import Decimal
        self.assertEqual(self._callFUT([Text(), 0]), False)
        self.assertEqual(
            self._callFUT([Text(), Bytes(), Int(), Float(), Decimal(), 0]),
            False
        )


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(Test__is_field),
        unittest.makeSuite(Test__fields),
    ))
