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
from guillotina.schema._field import (
    ASCII,
    URI,
    ASCIILine,
    Bool,
    Bytes,
    BytesLine,
    Choice,
    Container,
    Date,
    Datetime,
    Decimal,
    Dict,
    DottedName,
    Field,
    Float,
    FrozenSet,
    Id,
    Int,
    InterfaceField,
    Iterable,
    JSONField,
    List,
    MaskTextLine,
    MinMaxLen,
    NativeString,
    NativeStringLine,
    Object,
    Orderable,
    OrderedDict,
    Password,
    Set,
    SourceText,
    Text,
    TextLine,
    Time,
    Timedelta,
    Tuple,
    UnionField,
)
from guillotina.schema._schema import (
    get_fields,
    get_fields_in_order,
    getFieldNames,
    getFieldNamesInOrder,
    getSchemaValidationErrors,
    getValidationErrors,
)
from guillotina.schema.accessors import accessors
from guillotina.schema.exceptions import ValidationError


getFields = get_fields  # b/w
getFieldsInOrder = get_fields_in_order  # b/w

# pep 8 friendlyness
ASCII, ASCIILine, Bool, Bytes, BytesLine, Choice, Container, Date, Datetime
Decimal, Dict, DottedName, Field, Float, FrozenSet, Id, Int, InterfaceField
Iterable, List, MaskTextLine, MinMaxLen, NativeString, NativeStringLine, Object, Orderable
Password, Set, SourceText, Text, TextLine, Time, Timedelta, Tuple, URI, UnionField
get_fields, get_fields_in_order, getFieldNames, getFieldNamesInOrder,
getValidationErrors, getSchemaValidationErrors, JSONField, OrderedDict
accessors
ValidationError
NO_VALUE
