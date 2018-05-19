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


class BytesTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Bytes
        return Bytes

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IBytes(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IBytes
        verifyClass(IBytes, self._getTargetClass())

    def test_instance_conforms_to_IBytes(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IBytes
        verifyObject(IBytes, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
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
        self.assertRaises(ValidationError, self._makeOne, default='')

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(b'')
        field.validate(b'abc')
        field.validate(b'abc\ndef')
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(b'')
        field.validate(b'abc')
        field.validate(b'abc\ndef')
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_from_unicode_miss(self):
        byt = self._makeOne()
        self.assertRaises(UnicodeEncodeError, byt.from_unicode, chr(129))

    def test_from_unicode_hit(self):
        byt = self._makeOne()
        self.assertEqual(byt.from_unicode(''), b'')
        self.assertEqual(byt.from_unicode('DEADBEEF'), b'DEADBEEF')


class ASCIITests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import ASCII
        return ASCII

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IASCII(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IASCII
        verifyClass(IASCII, self._getTargetClass())

    def test_instance_conforms_to_IASCII(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IASCII
        verifyObject(IASCII, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        from guillotina.schema.utils import non_native_string
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, non_native_string(''))
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test__validate_empty(self):
        asc = self._makeOne()
        asc._validate('')  # no error

    def test__validate_non_empty_miss(self):
        from guillotina.schema.exceptions import InvalidValue
        asc = self._makeOne()
        self.assertRaises(InvalidValue, asc._validate, chr(129))

    def test__validate_non_empty_hit(self):
        asc = self._makeOne()
        for i in range(128):
            asc._validate(chr(i))  # doesn't raise


class BytesLineTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import BytesLine
        return BytesLine

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IBytesLine(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IBytesLine
        verifyClass(IBytesLine, self._getTargetClass())

    def test_instance_conforms_to_IBytesLine(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IBytesLine
        verifyObject(IBytesLine, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
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
        field.validate(None)
        field.validate(b'')
        field.validate(b'abc')
        field.validate(b'\xab\xde')

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(b'')
        field.validate(b'abc')
        field.validate(b'\xab\xde')
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_constraint(self):
        field = self._makeOne()
        self.assertEqual(field.constraint(b''), True)
        self.assertEqual(field.constraint(b'abc'), True)
        self.assertEqual(field.constraint(b'abc'), True)
        self.assertEqual(field.constraint(b'\xab\xde'), True)
        self.assertEqual(field.constraint(b'abc\ndef'), False)


class ASCIILineTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import ASCIILine
        return ASCIILine

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IASCIILine(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IASCIILine
        verifyClass(IASCIILine, self._getTargetClass())

    def test_instance_conforms_to_IASCIILine(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IASCIILine
        verifyObject(IASCIILine, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        from guillotina.schema.utils import non_native_string
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, non_native_string(''))
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        from guillotina.schema.exceptions import InvalidValue
        field = self._makeOne(required=False)
        field.validate(None)
        field.validate('')
        field.validate('abc')
        self.assertRaises(InvalidValue, field.validate, '\xab\xde')

    def test_validate_required(self):
        from guillotina.schema.exceptions import InvalidValue
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate('')
        field.validate('abc')
        self.assertRaises(InvalidValue, field.validate, '\xab\xde')
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_constraint(self):
        field = self._makeOne()
        self.assertEqual(field.constraint(''), True)
        self.assertEqual(field.constraint('abc'), True)
        self.assertEqual(field.constraint('abc'), True)
        # Non-ASCII byltes get checked in '_validate'.
        self.assertEqual(field.constraint('\xab\xde'), True)
        self.assertEqual(field.constraint('abc\ndef'), False)


class FloatTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Float
        return Float

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IFloat(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IFloat
        verifyClass(IFloat, self._getTargetClass())

    def test_instance_conforms_to_IFloat(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IFloat
        verifyObject(IFloat, self._makeOne())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(None)
        field.validate(10.0)
        field.validate(0.93)
        field.validate(1000.0003)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(10.0)
        field.validate(0.93)
        field.validate(1000.0003)
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min(self):
        from guillotina.schema.exceptions import TooSmall
        field = self._makeOne(min=10.5)
        field.validate(10.6)
        field.validate(20.2)
        self.assertRaises(TooSmall, field.validate, -9.0)
        self.assertRaises(TooSmall, field.validate, 10.4)

    def test_validate_max(self):
        from guillotina.schema.exceptions import TooBig
        field = self._makeOne(max=10.5)
        field.validate(5.3)
        field.validate(-9.1)
        self.assertRaises(TooBig, field.validate, 10.51)
        self.assertRaises(TooBig, field.validate, 20.7)

    def test_validate_min_and_max(self):
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall
        field = self._makeOne(min=-0.6, max=10.1)
        field.validate(0.0)
        field.validate(-0.03)
        field.validate(10.0001)
        self.assertRaises(TooSmall, field.validate, -10.0)
        self.assertRaises(TooSmall, field.validate, -1.6)
        self.assertRaises(TooBig, field.validate, 11.45)
        self.assertRaises(TooBig, field.validate, 20.02)

    def test_from_unicode_miss(self):
        flt = self._makeOne()
        self.assertRaises(ValueError, flt.from_unicode, '')
        self.assertRaises(ValueError, flt.from_unicode, 'abc')
        self.assertRaises(ValueError, flt.from_unicode, '14.G')

    def test_from_unicode_hit(self):
        flt = self._makeOne()
        self.assertEqual(flt.from_unicode('0'), 0.0)
        self.assertEqual(flt.from_unicode('1.23'), 1.23)
        self.assertEqual(flt.from_unicode('1.23e6'), 1230000.0)


class DecimalTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Decimal
        return Decimal

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IDecimal(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IDecimal
        verifyClass(IDecimal, self._getTargetClass())

    def test_instance_conforms_to_IDecimal(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IDecimal
        verifyObject(IDecimal, self._makeOne())

    def test_validate_not_required(self):
        import decimal
        field = self._makeOne(required=False)
        field.validate(decimal.Decimal("10.0"))
        field.validate(decimal.Decimal("0.93"))
        field.validate(decimal.Decimal("1000.0003"))
        field.validate(None)

    def test_validate_required(self):
        import decimal
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(decimal.Decimal("10.0"))
        field.validate(decimal.Decimal("0.93"))
        field.validate(decimal.Decimal("1000.0003"))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min(self):
        import decimal
        from guillotina.schema.exceptions import TooSmall
        field = self._makeOne(min=decimal.Decimal("10.5"))
        field.validate(decimal.Decimal("10.6"))
        field.validate(decimal.Decimal("20.2"))
        self.assertRaises(TooSmall, field.validate, decimal.Decimal("-9.0"))
        self.assertRaises(TooSmall, field.validate, decimal.Decimal("10.4"))

    def test_validate_max(self):
        import decimal
        from guillotina.schema.exceptions import TooBig
        field = self._makeOne(max=decimal.Decimal("10.5"))
        field.validate(decimal.Decimal("5.3"))
        field.validate(decimal.Decimal("-9.1"))
        self.assertRaises(TooBig, field.validate, decimal.Decimal("10.51"))
        self.assertRaises(TooBig, field.validate, decimal.Decimal("20.7"))

    def test_validate_min_and_max(self):
        import decimal
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall
        field = self._makeOne(min=decimal.Decimal("-0.6"),
                              max=decimal.Decimal("10.1"))
        field.validate(decimal.Decimal("0.0"))
        field.validate(decimal.Decimal("-0.03"))
        field.validate(decimal.Decimal("10.0001"))
        self.assertRaises(TooSmall, field.validate, decimal.Decimal("-10.0"))
        self.assertRaises(TooSmall, field.validate, decimal.Decimal("-1.6"))
        self.assertRaises(TooBig, field.validate, decimal.Decimal("11.45"))
        self.assertRaises(TooBig, field.validate, decimal.Decimal("20.02"))

    def test_from_unicode_miss(self):
        flt = self._makeOne()
        self.assertRaises(ValueError, flt.from_unicode, '')
        self.assertRaises(ValueError, flt.from_unicode, 'abc')
        self.assertRaises(ValueError, flt.from_unicode, '1.4G')

    def test_from_unicode_hit(self):
        from decimal import Decimal
        flt = self._makeOne()
        self.assertEqual(flt.from_unicode('0'), Decimal('0.0'))
        self.assertEqual(flt.from_unicode('1.23'), Decimal('1.23'))
        self.assertEqual(flt.from_unicode('12345.6'), Decimal('12345.6'))


class DatetimeTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Datetime
        return Datetime

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IDatetime(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IDatetime
        verifyClass(IDatetime, self._getTargetClass())

    def test_instance_conforms_to_IDatetime(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IDatetime
        verifyObject(IDatetime, self._makeOne())

    def test_validate_wrong_types(self):
        from datetime import date
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, b'')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())
        self.assertRaises(WrongType, field.validate, date.today())

    def test_validate_not_required(self):
        from datetime import datetime
        field = self._makeOne(required=False)
        field.validate(None)  # doesn't raise
        field.validate(datetime.now())  # doesn't raise

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne(required=True)
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_w_min(self):
        from datetime import datetime
        from guillotina.schema.exceptions import TooSmall
        d1 = datetime(2000, 10, 1)
        d2 = datetime(2000, 10, 2)
        field = self._makeOne(min=d1)
        field.validate(d1)  # doesn't raise
        field.validate(d2)  # doesn't raise
        self.assertRaises(TooSmall, field.validate, datetime(2000, 9, 30))

    def test_validate_w_max(self):
        from datetime import datetime
        from guillotina.schema.exceptions import TooBig
        d1 = datetime(2000, 10, 1)
        d2 = datetime(2000, 10, 2)
        d3 = datetime(2000, 10, 3)
        field = self._makeOne(max=d2)
        field.validate(d1)  # doesn't raise
        field.validate(d2)  # doesn't raise
        self.assertRaises(TooBig, field.validate, d3)

    def test_validate_w_min_and_max(self):
        from datetime import datetime
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall
        d1 = datetime(2000, 10, 1)
        d2 = datetime(2000, 10, 2)
        d3 = datetime(2000, 10, 3)
        d4 = datetime(2000, 10, 4)
        d5 = datetime(2000, 10, 5)
        field = self._makeOne(min=d2, max=d4)
        field.validate(d2)  # doesn't raise
        field.validate(d3)  # doesn't raise
        field.validate(d4)  # doesn't raise
        self.assertRaises(TooSmall, field.validate, d1)
        self.assertRaises(TooBig, field.validate, d5)


class DateTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Date
        return Date

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IDate(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IDate
        verifyClass(IDate, self._getTargetClass())

    def test_instance_conforms_to_IDate(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IDate
        verifyObject(IDate, self._makeOne())

    def test_validate_wrong_types(self):
        from datetime import datetime
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, b'')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())
        self.assertRaises(WrongType, field.validate, datetime.now())

    def test_validate_not_required(self):
        from datetime import date
        field = self._makeOne(required=False)
        field.validate(None)
        field.validate(date.today())

    def test_validate_required(self):
        from datetime import datetime
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(datetime.now().date())
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_w_min(self):
        from datetime import date
        from datetime import datetime
        from guillotina.schema.exceptions import TooSmall
        d1 = date(2000, 10, 1)
        d2 = date(2000, 10, 2)
        field = self._makeOne(min=d1)
        field.validate(d1)
        field.validate(d2)
        field.validate(datetime.now().date())
        self.assertRaises(TooSmall, field.validate, date(2000, 9, 30))

    def test_validate_w_max(self):
        from datetime import date
        from guillotina.schema.exceptions import TooBig
        d1 = date(2000, 10, 1)
        d2 = date(2000, 10, 2)
        d3 = date(2000, 10, 3)
        field = self._makeOne(max=d2)
        field.validate(d1)
        field.validate(d2)
        self.assertRaises(TooBig, field.validate, d3)

    def test_validate_w_min_and_max(self):
        from datetime import date
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall
        d1 = date(2000, 10, 1)
        d2 = date(2000, 10, 2)
        d3 = date(2000, 10, 3)
        d4 = date(2000, 10, 4)
        d5 = date(2000, 10, 5)
        field = self._makeOne(min=d2, max=d4)
        field.validate(d2)
        field.validate(d3)
        field.validate(d4)
        self.assertRaises(TooSmall, field.validate, d1)
        self.assertRaises(TooBig, field.validate, d5)


class TimedeltaTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Timedelta
        return Timedelta

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_ITimedelta(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import ITimedelta
        verifyClass(ITimedelta, self._getTargetClass())

    def test_instance_conforms_to_ITimedelta(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import ITimedelta
        verifyObject(ITimedelta, self._makeOne())

    def test_validate_not_required(self):
        from datetime import timedelta
        field = self._makeOne(required=False)
        field.validate(None)
        field.validate(timedelta(minutes=15))

    def test_validate_required(self):
        from datetime import timedelta
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(timedelta(minutes=15))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min(self):
        from datetime import timedelta
        from guillotina.schema.exceptions import TooSmall
        t1 = timedelta(hours=2)
        t2 = timedelta(hours=3)
        field = self._makeOne(min=t1)
        field.validate(t1)
        field.validate(t2)
        self.assertRaises(TooSmall, field.validate, timedelta(hours=1))

    def test_validate_max(self):
        from datetime import timedelta
        from guillotina.schema.exceptions import TooBig
        t1 = timedelta(minutes=1)
        t2 = timedelta(minutes=2)
        t3 = timedelta(minutes=3)
        field = self._makeOne(max=t2)
        field.validate(t1)
        field.validate(t2)
        self.assertRaises(TooBig, field.validate, t3)

    def test_validate_min_and_max(self):
        from datetime import timedelta
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall
        t1 = timedelta(days=1)
        t2 = timedelta(days=2)
        t3 = timedelta(days=3)
        t4 = timedelta(days=4)
        t5 = timedelta(days=5)
        field = self._makeOne(min=t2, max=t4)
        field.validate(t2)
        field.validate(t3)
        field.validate(t4)
        self.assertRaises(TooSmall, field.validate, t1)
        self.assertRaises(TooBig, field.validate, t5)


class TimeTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Time
        return Time

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_ITime(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import ITime
        verifyClass(ITime, self._getTargetClass())

    def test_instance_conforms_to_ITime(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import ITime
        verifyObject(ITime, self._makeOne())

    def test_validate_not_required(self):
        from datetime import time
        field = self._makeOne(required=False)
        field.validate(None)
        field.validate(time(12, 15, 37))

    def test_validate_required(self):
        from datetime import time
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(time(12, 15, 37))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min(self):
        from datetime import time
        from guillotina.schema.exceptions import TooSmall
        t1 = time(12, 15, 37)
        t2 = time(12, 25, 18)
        t3 = time(12, 42, 43)
        field = self._makeOne(min=t2)
        field.validate(t2)
        field.validate(t3)
        self.assertRaises(TooSmall, field.validate, t1)

    def test_validate_max(self):
        from datetime import time
        from guillotina.schema.exceptions import TooBig
        t1 = time(12, 15, 37)
        t2 = time(12, 25, 18)
        t3 = time(12, 42, 43)
        field = self._makeOne(max=t2)
        field.validate(t1)
        field.validate(t2)
        self.assertRaises(TooBig, field.validate, t3)

    def test_validate_min_and_max(self):
        from datetime import time
        from guillotina.schema.exceptions import TooBig
        from guillotina.schema.exceptions import TooSmall
        t1 = time(12, 15, 37)
        t2 = time(12, 25, 18)
        t3 = time(12, 42, 43)
        t4 = time(13, 7, 12)
        t5 = time(14, 22, 9)
        field = self._makeOne(min=t2, max=t4)
        field.validate(t2)
        field.validate(t3)
        field.validate(t4)
        self.assertRaises(TooSmall, field.validate, t1)
        self.assertRaises(TooBig, field.validate, t5)


class ChoiceTests(unittest.TestCase):

    def setUp(self):
        from guillotina.schema.vocabulary import _clear
        _clear()

    def tearDown(self):
        from guillotina.schema.vocabulary import _clear
        _clear()

    def _getTargetClass(self):
        from guillotina.schema._field import Choice
        return Choice

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IChoice(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IChoice
        verifyClass(IChoice, self._getTargetClass())

    def test_instance_conforms_to_IChoice(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IChoice
        verifyObject(IChoice, self._makeOne(values=[1, 2, 3]))

    def test_ctor_wo_values_vocabulary_or_source(self):
        self.assertRaises(ValueError, self._makeOne)

    def test_ctor_invalid_vocabulary(self):
        self.assertRaises(ValueError, self._makeOne, vocabulary=object())

    def test_ctor_invalid_source(self):
        self.assertRaises(ValueError, self._makeOne, source=object())

    def test_ctor_both_vocabulary_and_source(self):
        self.assertRaises(
            ValueError,
            self._makeOne, vocabulary='voc.name', source=object()
        )

    def test_ctor_both_vocabulary_and_values(self):
        self.assertRaises(ValueError,
                          self._makeOne, vocabulary='voc.name', values=[1, 2])

    def test_ctor_w_values(self):
        from guillotina.schema.vocabulary import SimpleVocabulary
        choose = self._makeOne(values=[1, 2])
        self.assertTrue(isinstance(choose.vocabulary, SimpleVocabulary))
        self.assertEqual(sorted(choose.vocabulary.by_value.keys()), [1, 2])
        self.assertEqual(sorted(choose.source.by_value.keys()), [1, 2])

    def test_ctor_w_named_vocabulary(self):
        choose = self._makeOne(vocabulary="vocab")
        self.assertEqual(choose.vocabularyName, 'vocab')

    def test_ctor_w_preconstructed_vocabulary(self):
        v = _makeSampleVocabulary()
        choose = self._makeOne(vocabulary=v)
        self.assertTrue(choose.vocabulary is v)
        self.assertTrue(choose.vocabularyName is None)

    def test_bind_w_preconstructed_vocabulary(self):
        from guillotina.schema.exceptions import ValidationError
        from guillotina.schema.vocabulary import setVocabularyRegistry
        v = _makeSampleVocabulary()
        setVocabularyRegistry(_makeDummyRegistry(v))
        choose = self._makeOne(vocabulary='vocab')
        bound = choose.bind(None)
        self.assertEqual(bound.vocabulary, v)
        self.assertEqual(bound.vocabularyName, 'vocab')
        bound.default = 1
        self.assertEqual(bound.default, 1)

        def _provoke(bound):
            bound.default = 42

        self.assertRaises(ValidationError, _provoke, bound)

    def test_bind_w_voc_not_ICSB(self):
        from zope.interface import implementer
        from guillotina.schema.interfaces import ISource
        from guillotina.schema.interfaces import IBaseVocabulary

        @implementer(IBaseVocabulary)
        @implementer(ISource)
        class Vocab(object):
            def __init__(self):
                pass

        source = self._makeOne(vocabulary=Vocab())
        instance = DummyInstance()
        target = source.bind(instance)
        self.assertTrue(target.vocabulary is source.vocabulary)

    def test_bind_w_voc_is_ICSB(self):
        from zope.interface import implementer
        from guillotina.schema.interfaces import IContextSourceBinder
        from guillotina.schema.interfaces import ISource

        @implementer(IContextSourceBinder)
        @implementer(ISource)
        class Vocab(object):
            def __init__(self, context):
                self.context = context

            def __call__(self, context):
                return self.__class__(context)

        # Chicken-egg
        source = self._makeOne(vocabulary='temp')
        source.vocabulary = Vocab(source)
        source.vocabularyName = None
        instance = DummyInstance()
        target = source.bind(instance)
        self.assertEqual(target.vocabulary.context, instance)

    def test_bind_w_voc_is_ICSB_but_not_ISource(self):
        from zope.interface import implementer
        from guillotina.schema.interfaces import IContextSourceBinder

        @implementer(IContextSourceBinder)
        class Vocab(object):
            def __init__(self, context):
                self.context = context

            def __call__(self, context):
                return self.__class__(context)

        # Chicken-egg
        source = self._makeOne(vocabulary='temp')
        source.vocabulary = Vocab(source)
        source.vocabularyName = None
        instance = DummyInstance()
        self.assertRaises(ValueError, source.bind, instance)

    def test_from_unicode_miss(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        flt = self._makeOne(values=('foo', 'bar', 'baz'))
        self.assertRaises(ConstraintNotSatisfied, flt.from_unicode, '')
        self.assertRaises(ConstraintNotSatisfied, flt.from_unicode, 'abc')
        self.assertRaises(ConstraintNotSatisfied, flt.from_unicode, '1.4G')

    def test_from_unicode_hit(self):
        flt = self._makeOne(values=('foo', 'bar', 'baz'))
        self.assertEqual(flt.from_unicode('foo'), 'foo')
        self.assertEqual(flt.from_unicode('bar'), 'bar')
        self.assertEqual(flt.from_unicode('baz'), 'baz')

    def test__validate_int(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        choice = self._makeOne(values=[1, 3])
        choice._validate(1)  # doesn't raise
        choice._validate(3)  # doesn't raise
        self.assertRaises(ConstraintNotSatisfied, choice._validate, 4)

    def test__validate_string(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        choice = self._makeOne(values=['a', 'c'])
        choice._validate('a')  # doesn't raise
        choice._validate('c')  # doesn't raise
        choice._validate('c')  # doesn't raise
        self.assertRaises(ConstraintNotSatisfied, choice._validate, 'd')

    def test__validate_tuple(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        choice = self._makeOne(values=[(1, 2), (5, 6)])
        choice._validate((1, 2))  # doesn't raise
        choice._validate((5, 6))  # doesn't raise
        self.assertRaises(ConstraintNotSatisfied, choice._validate, [5, 6])
        self.assertRaises(ConstraintNotSatisfied, choice._validate, ())

    def test__validate_mixed(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        choice = self._makeOne(values=[1, 'b', (0.2,)])
        choice._validate(1)  # doesn't raise
        choice._validate('b')  # doesn't raise
        choice._validate((0.2,))  # doesn't raise
        self.assertRaises(ConstraintNotSatisfied, choice._validate, '1')
        self.assertRaises(ConstraintNotSatisfied, choice._validate, 0.2)

    def test__validate_w_named_vocabulary_invalid(self):
        choose = self._makeOne(vocabulary='vocab')
        self.assertRaises(ValueError, choose._validate, 42)

    def test__validate_w_named_vocabulary(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.vocabulary import setVocabularyRegistry
        v = _makeSampleVocabulary()
        setVocabularyRegistry(_makeDummyRegistry(v))
        choose = self._makeOne(vocabulary='vocab')
        choose._validate(1)
        choose._validate(3)
        self.assertRaises(ConstraintNotSatisfied, choose._validate, 42)

    def test__validate_source_is_ICSB_unbound(self):
        from zope.interface import implementer
        from guillotina.schema.interfaces import IContextSourceBinder

        @implementer(IContextSourceBinder)
        class SampleContextSourceBinder(object):
            def __call__(self, context):
                pass

        choice = self._makeOne(source=SampleContextSourceBinder())
        self.assertRaises(TypeError, choice.validate, 1)

    def test__validate_source_is_ICSB_bound(self):
        from zope.interface import implementer
        from guillotina.schema.interfaces import IContextSourceBinder
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.tests.test_vocabulary import _makeSampleVocabulary

        @implementer(IContextSourceBinder)
        class SampleContextSourceBinder(object):
            def __call__(self, context):
                return _makeSampleVocabulary()

        s = SampleContextSourceBinder()
        choice = self._makeOne(source=s)
        # raises not iterable with unbound field
        self.assertRaises(TypeError, choice.validate, 1)
        o = object()
        clone = choice.bind(o)
        clone._validate(1)
        clone._validate(3)
        self.assertRaises(ConstraintNotSatisfied, clone._validate, 42)


class URITests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import URI
        return URI

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IURI(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IURI
        verifyClass(IURI, self._getTargetClass())

    def test_instance_conforms_to_IURI(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IURI
        verifyObject(IURI, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        from guillotina.schema.utils import non_native_string
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, non_native_string(''))
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
        field.validate('http://example.com/')
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate('http://example.com/')
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_not_a_uri(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.exceptions import InvalidURI
        field = self._makeOne()
        self.assertRaises(InvalidURI, field.validate, '')
        self.assertRaises(InvalidURI, field.validate, 'abc')
        self.assertRaises(InvalidURI, field.validate, '\xab\xde')
        self.assertRaises(ConstraintNotSatisfied,
                          field.validate, 'http://example.com/\nDAV:')

    def test_from_unicode_ok(self):
        field = self._makeOne()
        self.assertEqual(field.from_unicode('http://example.com/'),
                         'http://example.com/')

    def test_from_unicode_invalid(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.exceptions import InvalidURI
        field = self._makeOne()
        self.assertRaises(InvalidURI, field.from_unicode, '')
        self.assertRaises(InvalidURI, field.from_unicode, 'abc')
        self.assertRaises(ConstraintNotSatisfied,
                          field.from_unicode, 'http://example.com/\nDAV:')


class DottedNameTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import DottedName
        return DottedName

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IDottedName(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IDottedName
        verifyClass(IDottedName, self._getTargetClass())

    def test_instance_conforms_to_IDottedName(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IDottedName
        verifyObject(IDottedName, self._makeOne())

    def test_ctor_defaults(self):
        dotted = self._makeOne()
        self.assertEqual(dotted.min_dots, 0)
        self.assertEqual(dotted.max_dots, None)

    def test_ctor_min_dots_invalid(self):
        self.assertRaises(ValueError, self._makeOne, min_dots=-1)

    def test_ctor_min_dots_valid(self):
        dotted = self._makeOne(min_dots=1)
        self.assertEqual(dotted.min_dots, 1)

    def test_ctor_max_dots_invalid(self):
        self.assertRaises(ValueError, self._makeOne, min_dots=2, max_dots=1)

    def test_ctor_max_dots_valid(self):
        dotted = self._makeOne(max_dots=2)
        self.assertEqual(dotted.max_dots, 2)

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        from guillotina.schema.utils import non_native_string
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, non_native_string(''))
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
        field.validate('name')
        field.validate('dotted.name')
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate('name')
        field.validate('dotted.name')
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_w_min_dots(self):
        from guillotina.schema.exceptions import InvalidDottedName
        field = self._makeOne(min_dots=1)
        self.assertRaises(InvalidDottedName, field.validate, 'name')
        field.validate('dotted.name')
        field.validate('moar.dotted.name')

    def test_validate_w_max_dots(self):
        from guillotina.schema.exceptions import InvalidDottedName
        field = self._makeOne(max_dots=1)
        field.validate('name')
        field.validate('dotted.name')
        self.assertRaises(InvalidDottedName,
                          field.validate, 'moar.dotted.name')

    def test_validate_not_a_dotted_name(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.exceptions import InvalidDottedName
        field = self._makeOne()
        self.assertRaises(InvalidDottedName, field.validate, '')
        self.assertRaises(InvalidDottedName, field.validate, '\xab\xde')
        self.assertRaises(ConstraintNotSatisfied,
                          field.validate, 'http://example.com/\nDAV:')

    def test_from_unicode_dotted_name_ok(self):
        field = self._makeOne()
        self.assertEqual(field.from_unicode('dotted.name'), 'dotted.name')

    def test_from_unicode_invalid(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.exceptions import InvalidDottedName
        field = self._makeOne()
        self.assertRaises(InvalidDottedName, field.from_unicode, '')
        self.assertRaises(ConstraintNotSatisfied,
                          field.from_unicode, 'http://example.com/\nDAV:')


class IdTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Id
        return Id

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IId(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IId
        verifyClass(IId, self._getTargetClass())

    def test_instance_conforms_to_IId(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IId
        verifyObject(IId, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        from guillotina.schema.utils import non_native_string
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, non_native_string(''))
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
        field.validate('http://example.com/')
        field.validate('dotted.name')
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate('http://example.com/')
        field.validate('dotted.name')
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_not_a_uri(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.exceptions import InvalidId
        field = self._makeOne()
        self.assertRaises(InvalidId, field.validate, '')
        self.assertRaises(InvalidId, field.validate, 'abc')
        self.assertRaises(InvalidId, field.validate, '\xab\xde')
        self.assertRaises(ConstraintNotSatisfied,
                          field.validate, 'http://example.com/\nDAV:')

    def test_from_unicode_url_ok(self):
        field = self._makeOne()
        self.assertEqual(field.from_unicode('http://example.com/'),
                         'http://example.com/')

    def test_from_unicode_dotted_name_ok(self):
        field = self._makeOne()
        self.assertEqual(field.from_unicode('dotted.name'), 'dotted.name')

    def test_from_unicode_invalid(self):
        from guillotina.schema.exceptions import ConstraintNotSatisfied
        from guillotina.schema.exceptions import InvalidId
        field = self._makeOne()
        self.assertRaises(InvalidId, field.from_unicode, '')
        self.assertRaises(InvalidId, field.from_unicode, 'abc')
        self.assertRaises(ConstraintNotSatisfied,
                          field.from_unicode, 'http://example.com/\nDAV:')


class InterfaceFieldTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import InterfaceField
        return InterfaceField

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IInterfaceField(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IInterfaceField
        verifyClass(IInterfaceField, self._getTargetClass())

    def test_instance_conforms_to_IInterfaceField(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IInterfaceField
        verifyObject(IInterfaceField, self._makeOne())

    def test_validate_wrong_types(self):
        from datetime import date
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, b'')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())
        self.assertRaises(WrongType, field.validate, date.today())

    def test_validate_not_required(self):
        from zope.interface import Interface

        class DummyInterface(Interface):
            pass

        field = self._makeOne(required=False)
        field.validate(DummyInterface)
        field.validate(None)

    def test_validate_required(self):
        from zope.interface import Interface
        from guillotina.schema.exceptions import RequiredMissing

        class DummyInterface(Interface):
            pass

        field = self._makeOne(required=True)
        field.validate(DummyInterface)
        self.assertRaises(RequiredMissing, field.validate, None)


class AbstractCollectionTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import AbstractCollection
        return AbstractCollection

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_ctor_defaults(self):
        absc = self._makeOne()
        self.assertEqual(absc.value_type, None)
        self.assertEqual(absc.unique, False)

    def test_ctor_explicit(self):
        from guillotina.schema._bootstrapfields import Text
        text = Text()
        absc = self._makeOne(text, True)
        self.assertEqual(absc.value_type, text)
        self.assertEqual(absc.unique, True)

    def test_ctor_w_non_field_value_type(self):
        class NotAField(object):
            pass
        self.assertRaises(ValueError, self._makeOne, NotAField)

    def test_bind_wo_value_Type(self):
        absc = self._makeOne()
        context = object()
        bound = absc.bind(context)
        self.assertEqual(bound.context, context)
        self.assertEqual(bound.value_type, None)
        self.assertEqual(bound.unique, False)

    def test_bind_w_value_Type(self):
        from guillotina.schema._bootstrapfields import Text
        text = Text()
        absc = self._makeOne(text, True)
        context = object()
        bound = absc.bind(context)
        self.assertEqual(bound.context, context)
        self.assertEqual(isinstance(bound.value_type, Text), True)
        self.assertEqual(bound.value_type.context, context)
        self.assertEqual(bound.unique, True)

    def test__validate_wrong_contained_type(self):
        from guillotina.schema.exceptions import WrongContainedType
        from guillotina.schema._bootstrapfields import Text
        text = Text()
        absc = self._makeOne(text)
        self.assertRaises(WrongContainedType, absc.validate, [1])

    def test__validate_miss_uniqueness(self):
        from guillotina.schema.exceptions import NotUnique
        from guillotina.schema._bootstrapfields import Text
        text = Text()
        absc = self._makeOne(text, True)
        self.assertRaises(NotUnique, absc.validate, ['a', 'a'])


class TupleTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Tuple
        return Tuple

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_ITuple(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import ITuple
        verifyClass(ITuple, self._getTargetClass())

    def test_instance_conforms_to_ITuple(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import ITuple
        verifyObject(ITuple, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(())
        field.validate((1, 2))
        field.validate((3,))
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(())
        field.validate((1, 2))
        field.validate((3,))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min_length(self):
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=2)
        field.validate((1, 2))
        field.validate((1, 2, 3))
        self.assertRaises(TooShort, field.validate, ())
        self.assertRaises(TooShort, field.validate, (1,))

    def test_validate_max_length(self):
        from guillotina.schema.exceptions import TooLong
        field = self._makeOne(max_length=2)
        field.validate(())
        field.validate((1, 2))
        self.assertRaises(TooLong, field.validate, (1, 2, 3, 4))
        self.assertRaises(TooLong, field.validate, (1, 2, 3))

    def test_validate_min_length_and_max_length(self):
        from guillotina.schema.exceptions import TooLong
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=1, max_length=2)
        field.validate((1, ))
        field.validate((1, 2))
        self.assertRaises(TooShort, field.validate, ())
        self.assertRaises(TooLong, field.validate, (1, 2, 3))


class ListTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import List
        return List

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IList(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IList
        verifyClass(IList, self._getTargetClass())

    def test_instance_conforms_to_IList(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IList
        verifyObject(IList, self._makeOne())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate([])
        field.validate([1, 2])
        field.validate([3])
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate([])
        field.validate([1, 2])
        field.validate([3])
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min_length(self):
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=2)
        field.validate([1, 2])
        field.validate([1, 2, 3])
        self.assertRaises(TooShort, field.validate, [])
        self.assertRaises(TooShort, field.validate, [1, ])

    def test_validate_max_length(self):
        from guillotina.schema.exceptions import TooLong
        field = self._makeOne(max_length=2)
        field.validate([])
        field.validate([1])
        field.validate([1, 2])
        self.assertRaises(TooLong, field.validate, [1, 2, 3, 4])
        self.assertRaises(TooLong, field.validate, [1, 2, 3])

    def test_validate_min_length_and_max_length(self):
        from guillotina.schema.exceptions import TooLong
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=1, max_length=2)
        field.validate([1])
        field.validate([1, 2])
        self.assertRaises(TooShort, field.validate, [])
        self.assertRaises(TooLong, field.validate, [1, 2, 3])


class SetTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Set
        return Set

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_ISet(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import ISet
        verifyClass(ISet, self._getTargetClass())

    def test_instance_conforms_to_ISet(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import ISet
        verifyObject(ISet, self._makeOne())

    def test_ctor_disallows_unique(self):
        self.assertRaises(TypeError, self._makeOne, unique=False)
        self.assertRaises(TypeError, self._makeOne, unique=True)
        self.assertTrue(self._makeOne().unique)

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(set())
        field.validate(set((1, 2)))
        field.validate(set((3,)))
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(set())
        field.validate(set((1, 2)))
        field.validate(set((3,)))
        field.validate(set())
        field.validate(set((1, 2)))
        field.validate(set((3,)))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min_length(self):
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=2)
        field.validate(set((1, 2)))
        field.validate(set((1, 2, 3)))
        self.assertRaises(TooShort, field.validate, set())
        self.assertRaises(TooShort, field.validate, set((1,)))

    def test_validate_max_length(self):
        from guillotina.schema.exceptions import TooLong
        field = self._makeOne(max_length=2)
        field.validate(set())
        field.validate(set((1,)))
        field.validate(set((1, 2)))
        self.assertRaises(TooLong, field.validate, set((1, 2, 3, 4)))
        self.assertRaises(TooLong, field.validate, set((1, 2, 3)))

    def test_validate_min_length_and_max_length(self):
        from guillotina.schema.exceptions import TooLong
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=1, max_length=2)
        field.validate(set((1,)))
        field.validate(set((1, 2)))
        self.assertRaises(TooShort, field.validate, set())
        self.assertRaises(TooLong, field.validate, set((1, 2, 3)))


class FrozenSetTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import FrozenSet
        return FrozenSet

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IFrozenSet(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IFrozenSet
        verifyClass(IFrozenSet, self._getTargetClass())

    def test_instance_conforms_to_IFrozenSet(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IFrozenSet
        verifyObject(IFrozenSet, self._makeOne())

    def test_ctor_disallows_unique(self):
        self.assertRaises(TypeError, self._makeOne, unique=False)
        self.assertRaises(TypeError, self._makeOne, unique=True)
        self.assertTrue(self._makeOne().unique)

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, {})
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate(frozenset())
        field.validate(frozenset((1, 2)))
        field.validate(frozenset((3,)))
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate(frozenset())
        field.validate(frozenset((1, 2)))
        field.validate(frozenset((3,)))
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_min_length(self):
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=2)
        field.validate(frozenset((1, 2)))
        field.validate(frozenset((1, 2, 3)))
        self.assertRaises(TooShort, field.validate, frozenset())
        self.assertRaises(TooShort, field.validate, frozenset((1,)))

    def test_validate_max_length(self):
        from guillotina.schema.exceptions import TooLong
        field = self._makeOne(max_length=2)
        field.validate(frozenset())
        field.validate(frozenset((1,)))
        field.validate(frozenset((1, 2)))
        self.assertRaises(TooLong, field.validate, frozenset((1, 2, 3, 4)))
        self.assertRaises(TooLong, field.validate, frozenset((1, 2, 3)))

    def test_validate_min_length_and_max_length(self):
        from guillotina.schema.exceptions import TooLong
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=1, max_length=2)
        field.validate(frozenset((1,)))
        field.validate(frozenset((1, 2)))
        self.assertRaises(TooShort, field.validate, frozenset())
        self.assertRaises(TooLong, field.validate, frozenset((1, 2, 3)))


class ObjectTests(unittest.TestCase):

    def setUp(self):
        from guillotina.component.event import sync_subscribers
        self._before = sync_subscribers[:]

    def tearDown(self):
        from guillotina.component.event import sync_subscribers
        sync_subscribers[:] = self._before

    def _getTargetClass(self):
        from guillotina.schema._field import Object
        return Object

    def _makeOne(self, schema=None, *args, **kw):
        if schema is None:
            schema = self._makeSchema()
        return self._getTargetClass()(schema, *args, **kw)

    def _makeSchema(self, **kw):
        from zope.interface import Interface
        from zope.interface.interface import InterfaceClass
        return InterfaceClass('ISchema', (Interface,), kw)

    def _getErrors(self, f, *args, **kw):
        from guillotina.schema.exceptions import WrongContainedType
        try:
            f(*args, **kw)
        except WrongContainedType as e:
            try:
                return e.args[0]
            except:
                return []
        self.fail('Expected WrongContainedType Error')

    def _makeCycles(self):
        from zope.interface import Interface
        from zope.interface import implementer
        from guillotina.schema import Object
        from guillotina.schema import List
        from guillotina.schema._messageid import _

        class IUnit(Interface):
            """A schema that participate to a cycle"""
            boss = Object(
                schema=Interface,
                title=_("Boss"),
                description=_("Boss description"),
                required=False,
                )
            members = List(
                value_type=Object(schema=Interface),
                title=_("Member List"),
                description=_("Member list description"),
                required=False,
                )

        class IPerson(Interface):
            """A schema that participate to a cycle"""
            unit = Object(
                schema=IUnit,
                title=_("Unit"),
                description=_("Unit description"),
                required=False,
                )

        IUnit['boss'].schema = IPerson
        IUnit['members'].value_type.schema = IPerson

        @implementer(IUnit)
        class Unit(object):
            def __init__(self, person, person_list):
                self.boss = person
                self.members = person_list

        @implementer(IPerson)
        class Person(object):
            def __init__(self, unit):
                self.unit = unit

        return IUnit, Person, Unit

    def test_class_conforms_to_IObject(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IObject
        verifyClass(IObject, self._getTargetClass())

    def test_instance_conforms_to_IObject(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IObject
        verifyObject(IObject, self._makeOne())

    def test_ctor_w_bad_schema(self):
        from guillotina.schema.exceptions import WrongType
        self.assertRaises(WrongType, self._makeOne, object())

    def test_validate_not_required(self):
        schema = self._makeSchema()
        objf = self._makeOne(schema, required=False)
        objf.validate(None)  # doesn't raise

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne(required=True)
        self.assertRaises(RequiredMissing, field.validate, None)

    def test__validate_w_empty_schema(self):
        from zope.interface import Interface
        objf = self._makeOne(Interface)
        objf.validate(object())  # doesn't raise

    def test__validate_w_value_not_providing_schema(self):
        from guillotina.schema.exceptions import SchemaNotProvided
        from guillotina.schema._bootstrapfields import Text
        schema = self._makeSchema(foo=Text(), bar=Text())
        objf = self._makeOne(schema)
        self.assertRaises(SchemaNotProvided, objf.validate, object())

    def test__validate_w_value_providing_schema_but_missing_fields(self):
        from zope.interface import implementer
        from guillotina.schema.exceptions import RequiredMissing
        from guillotina.schema.exceptions import WrongContainedType
        from guillotina.schema._bootstrapfields import Text
        schema = self._makeSchema(foo=Text(), bar=Text())

        @implementer(schema)
        class Broken(object):
            pass

        objf = self._makeOne(schema)
        self.assertRaises(WrongContainedType, objf.validate, Broken())
        errors = self._getErrors(objf.validate, Broken())
        self.assertEqual(len(errors), 2)
        errors = sorted(errors,
                        key=lambda x: (type(x).__name__, str(x.args[0])))
        err = errors[0]
        self.assertTrue(isinstance(err, RequiredMissing))

    def test__validate_w_value_providing_schema_but_invalid_fields(self):
        from zope.interface import implementer
        from guillotina.schema.exceptions import WrongContainedType
        from guillotina.schema.exceptions import RequiredMissing
        from guillotina.schema.exceptions import WrongType
        from guillotina.schema._bootstrapfields import Text
        schema = self._makeSchema(foo=Text(), bar=Text())

        @implementer(schema)
        class Broken(object):
            foo = None
            bar = 1

        objf = self._makeOne(schema)
        self.assertRaises(WrongContainedType, objf.validate, Broken())
        errors = self._getErrors(objf.validate, Broken())
        self.assertEqual(len(errors), 2)
        errors = sorted(errors, key=lambda x: type(x).__name__)
        err = errors[0]
        self.assertTrue(isinstance(err, RequiredMissing))
        self.assertEqual(err.args, ('foo',))
        err = errors[1]
        self.assertTrue(isinstance(err, WrongType))
        self.assertEqual(err.args, (1, str, 'bar'))

    def test__validate_w_value_providing_schema(self):
        from zope.interface import implementer
        from guillotina.schema._bootstrapfields import Text
        from guillotina.schema._field import Choice
        schema = self._makeSchema(
            foo=Text(),
            bar=Text(),
            baz=Choice(values=[1, 2, 3]),
        )

        @implementer(schema)
        class OK(object):
            foo = 'Foo'
            bar = 'Bar'
            baz = 2
        objf = self._makeOne(schema)
        objf.validate(OK())  # doesn't raise

    def test_validate_w_cycles(self):
        IUnit, Person, Unit = self._makeCycles()
        field = self._makeOne(schema=IUnit)
        person1 = Person(None)
        person2 = Person(None)
        unit = Unit(person1, [person1, person2])
        person1.unit = unit
        person2.unit = unit
        field.validate(unit)  # doesn't raise

    def test_validate_w_cycles_object_not_valid(self):
        from guillotina.schema.exceptions import WrongContainedType
        IUnit, Person, Unit = self._makeCycles()
        field = self._makeOne(schema=IUnit)
        person1 = Person(None)
        person2 = Person(None)
        person3 = Person(DummyInstance())
        unit = Unit(person3, [person1, person2])
        person1.unit = unit
        person2.unit = unit
        self.assertRaises(WrongContainedType, field.validate, unit)

    def test_validate_w_cycles_collection_not_valid(self):
        from guillotina.schema.exceptions import WrongContainedType
        IUnit, Person, Unit = self._makeCycles()
        field = self._makeOne(schema=IUnit)
        person1 = Person(None)
        person2 = Person(None)
        person3 = Person(DummyInstance())
        unit = Unit(person1, [person2, person3])
        person1.unit = unit
        person2.unit = unit
        self.assertRaises(WrongContainedType, field.validate, unit)


class DictTests(unittest.TestCase):

    def _getTargetClass(self):
        from guillotina.schema._field import Dict
        return Dict

    def _makeOne(self, *args, **kw):
        return self._getTargetClass()(*args, **kw)

    def test_class_conforms_to_IDict(self):
        from zope.interface.verify import verifyClass
        from guillotina.schema.interfaces import IDict
        verifyClass(IDict, self._getTargetClass())

    def test_instance_conforms_to_IDict(self):
        from zope.interface.verify import verifyObject
        from guillotina.schema.interfaces import IDict
        verifyObject(IDict, self._makeOne())

    def test_ctor_key_type_not_IField(self):
        self.assertRaises(ValueError, self._makeOne, key_type=object())

    def test_ctor_value_type_not_IField(self):
        self.assertRaises(ValueError, self._makeOne, value_type=object())

    def test_validate_wrong_types(self):
        from guillotina.schema.exceptions import WrongType
        field = self._makeOne()
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, '')
        self.assertRaises(WrongType, field.validate, 1)
        self.assertRaises(WrongType, field.validate, 1.0)
        self.assertRaises(WrongType, field.validate, ())
        self.assertRaises(WrongType, field.validate, [])
        self.assertRaises(WrongType, field.validate, set())
        self.assertRaises(WrongType, field.validate, frozenset())
        self.assertRaises(WrongType, field.validate, object())

    def test_validate_not_required(self):
        field = self._makeOne(required=False)
        field.validate({})
        field.validate({1: 'b', 2: 'd'})
        field.validate({3: 'a'})
        field.validate(None)

    def test_validate_required(self):
        from guillotina.schema.exceptions import RequiredMissing
        field = self._makeOne()
        field.validate({})
        field.validate({1: 'b', 2: 'd'})
        field.validate({3: 'a'})
        self.assertRaises(RequiredMissing, field.validate, None)

    def test_validate_invalid_key_type(self):
        from guillotina.schema.exceptions import WrongContainedType
        from guillotina.schema._bootstrapfields import Int
        field = self._makeOne(key_type=Int())
        field.validate({})
        field.validate({1: 'b', 2: 'd'})
        field.validate({3: 'a'})
        self.assertRaises(WrongContainedType, field.validate, {'a': 1})

    def test_validate_invalid_value_type(self):
        from guillotina.schema.exceptions import WrongContainedType
        from guillotina.schema._bootstrapfields import Int
        field = self._makeOne(value_type=Int())
        field.validate({})
        field.validate({'b': 1, 'd': 2})
        field.validate({'a': 3})
        self.assertRaises(WrongContainedType, field.validate, {1: 'a'})

    def test_validate_min_length(self):
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=1)
        field.validate({1: 'a'})
        field.validate({1: 'a', 2: 'b'})
        self.assertRaises(TooShort, field.validate, {})

    def test_validate_max_length(self):
        from guillotina.schema.exceptions import TooLong
        field = self._makeOne(max_length=1)
        field.validate({})
        field.validate({1: 'a'})
        self.assertRaises(TooLong, field.validate, {1: 'a', 2: 'b'})
        self.assertRaises(TooLong, field.validate, {1: 'a', 2: 'b', 3: 'c'})

    def test_validate_min_length_and_max_length(self):
        from guillotina.schema.exceptions import TooLong
        from guillotina.schema.exceptions import TooShort
        field = self._makeOne(min_length=1, max_length=2)
        field.validate({1: 'a'})
        field.validate({1: 'a', 2: 'b'})
        self.assertRaises(TooShort, field.validate, {})
        self.assertRaises(TooLong, field.validate, {1: 'a', 2: 'b', 3: 'c'})

    def test_bind_binds_key_and_value_types(self):
        from guillotina.schema import Int
        field = self._makeOne(key_type=Int(), value_type=Int())
        context = DummyInstance()
        field2 = field.bind(context)
        self.assertEqual(field2.key_type.context, context)
        self.assertEqual(field2.value_type.context, context)


class DummyInstance(object):
    pass


def _makeSampleVocabulary():
    from zope.interface import implementer
    from guillotina.schema.interfaces import IVocabulary

    class SampleTerm(object):
        pass

    @implementer(IVocabulary)
    class SampleVocabulary(object):

        def __iter__(self):
            return iter([self.getTerm(x) for x in range(0, 10)])

        def __contains__(self, value):
            return 0 <= value < 10

        def __len__(self):
            return 10

        def getTerm(self, value):
            if value in self:
                t = SampleTerm()
                t.value = value
                t.double = 2 * value
                return t
            raise LookupError("no such value: %r" % value)

    return SampleVocabulary()


def _makeDummyRegistry(v):
    from guillotina.schema.vocabulary import VocabularyRegistry

    class DummyRegistry(VocabularyRegistry):
        def __init__(self, vocabulary):
            self._vocabulary = vocabulary

        def get(self, object, name):
            return self._vocabulary
    return DummyRegistry(v)


def test_suite():
    return unittest.TestSuite((
        unittest.makeSuite(BytesTests),
        unittest.makeSuite(ASCIITests),
        unittest.makeSuite(BytesLineTests),
        unittest.makeSuite(ASCIILineTests),
        unittest.makeSuite(FloatTests),
        unittest.makeSuite(DecimalTests),
        unittest.makeSuite(DatetimeTests),
        unittest.makeSuite(DateTests),
        unittest.makeSuite(TimedeltaTests),
        unittest.makeSuite(TimeTests),
        unittest.makeSuite(ChoiceTests),
        unittest.makeSuite(InterfaceFieldTests),
        unittest.makeSuite(AbstractCollectionTests),
        unittest.makeSuite(TupleTests),
        unittest.makeSuite(ListTests),
        unittest.makeSuite(SetTests),
        unittest.makeSuite(FrozenSetTests),
        unittest.makeSuite(ObjectTests),
        unittest.makeSuite(DictTests),
        unittest.makeSuite(URITests),
        unittest.makeSuite(IdTests),
        unittest.makeSuite(DottedNameTests),
    ))
