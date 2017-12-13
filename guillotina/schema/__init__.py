# XXX INFO
# This package is pulled out of guillotina.schema to give guillotina more control
# over our use of fields(async) and to also provide a nicer api and less dependencies
# in order to work with guillotina

##############################################################################
#
# Copyright (c) 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
##############################################################################

from guillotina.schema._bootstrapinterfaces import NO_VALUE
from guillotina.schema._field import ASCII
from guillotina.schema._field import ASCIILine
from guillotina.schema._field import Bool
from guillotina.schema._field import Bytes
from guillotina.schema._field import BytesLine
from guillotina.schema._field import Choice
from guillotina.schema._field import Container
from guillotina.schema._field import Date
from guillotina.schema._field import Datetime
from guillotina.schema._field import Decimal
from guillotina.schema._field import Dict
from guillotina.schema._field import DottedName
from guillotina.schema._field import Field
from guillotina.schema._field import Float
from guillotina.schema._field import FrozenSet
from guillotina.schema._field import Id
from guillotina.schema._field import Int
from guillotina.schema._field import InterfaceField
from guillotina.schema._field import Iterable
from guillotina.schema._field import JSONField
from guillotina.schema._field import List
from guillotina.schema._field import MinMaxLen
from guillotina.schema._field import NativeString
from guillotina.schema._field import NativeStringLine
from guillotina.schema._field import Object
from guillotina.schema._field import Orderable
from guillotina.schema._field import Password
from guillotina.schema._field import Set
from guillotina.schema._field import SourceText
from guillotina.schema._field import Text
from guillotina.schema._field import TextLine
from guillotina.schema._field import Time
from guillotina.schema._field import Timedelta
from guillotina.schema._field import Tuple
from guillotina.schema._field import URI
from guillotina.schema._schema import get_fields
from guillotina.schema._schema import get_fields_in_order
from guillotina.schema._schema import getFieldNames
from guillotina.schema._schema import getFieldNamesInOrder
from guillotina.schema._schema import getSchemaValidationErrors
from guillotina.schema._schema import getValidationErrors
from guillotina.schema.accessors import accessors
from guillotina.schema.exceptions import ValidationError


getFields = get_fields  # b/w
getFieldsInOrder = get_fields_in_order  # b/w

# pep 8 friendlyness
ASCII, ASCIILine, Bool, Bytes, BytesLine, Choice, Container, Date, Datetime
Decimal, Dict, DottedName, Field, Float, FrozenSet, Id, Int, InterfaceField
Iterable, List, MinMaxLen, NativeString, NativeStringLine, Object, Orderable
Password, Set, SourceText, Text, TextLine, Time, Timedelta, Tuple, URI
get_fields, get_fields_in_order, getFieldNames, getFieldNamesInOrder,
getValidationErrors, getSchemaValidationErrors, JSONField
accessors
ValidationError
NO_VALUE
