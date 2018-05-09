# -*- coding: utf-8 -*-
##############################################################################
# Copyright (c) 2002 Zope Foundation and Contributors.
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
from collections import namedtuple
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from guillotina.event import sync_notify
from guillotina.schema._bootstrapfields import Bool
from guillotina.schema._bootstrapfields import Container  # API import for __init__
from guillotina.schema._bootstrapfields import Field
from guillotina.schema._bootstrapfields import Int
from guillotina.schema._bootstrapfields import Iterable
from guillotina.schema._bootstrapfields import MinMaxLen
from guillotina.schema._bootstrapfields import Orderable
from guillotina.schema._bootstrapfields import Password
from guillotina.schema._bootstrapfields import Text
from guillotina.schema._bootstrapfields import TextLine
from guillotina.schema.exceptions import ConstraintNotSatisfied
from guillotina.schema.exceptions import InvalidDottedName
from guillotina.schema.exceptions import InvalidId
from guillotina.schema.exceptions import InvalidURI
from guillotina.schema.exceptions import InvalidValue
from guillotina.schema.exceptions import NotUnique
from guillotina.schema.exceptions import SchemaNotFullyImplemented
from guillotina.schema.exceptions import SchemaNotProvided
from guillotina.schema.exceptions import ValidationError
from guillotina.schema.exceptions import WrongContainedType
from guillotina.schema.exceptions import WrongType
from guillotina.schema.fieldproperty import FieldProperty
from guillotina.schema.interfaces import IASCII
from guillotina.schema.interfaces import IASCIILine
from guillotina.schema.interfaces import IBaseVocabulary
from guillotina.schema.interfaces import IBeforeObjectAssignedEvent
from guillotina.schema.interfaces import IBool
from guillotina.schema.interfaces import IBytes
from guillotina.schema.interfaces import IBytesLine
from guillotina.schema.interfaces import IChoice
from guillotina.schema.interfaces import IContextSourceBinder
from guillotina.schema.interfaces import IDate
from guillotina.schema.interfaces import IDatetime
from guillotina.schema.interfaces import IDecimal
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IDottedName
from guillotina.schema.interfaces import IField
from guillotina.schema.interfaces import IFloat
from guillotina.schema.interfaces import IFromUnicode
from guillotina.schema.interfaces import IFrozenSet
from guillotina.schema.interfaces import IId
from guillotina.schema.interfaces import IInt
from guillotina.schema.interfaces import IInterfaceField
from guillotina.schema.interfaces import IJSONField
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import IMinMaxLen
from guillotina.schema.interfaces import IObject
from guillotina.schema.interfaces import IPassword
from guillotina.schema.interfaces import ISet
from guillotina.schema.interfaces import ISource
from guillotina.schema.interfaces import ISourceText
from guillotina.schema.interfaces import IText
from guillotina.schema.interfaces import ITextLine
from guillotina.schema.interfaces import ITime
from guillotina.schema.interfaces import ITimedelta
from guillotina.schema.interfaces import ITuple
from guillotina.schema.interfaces import IURI
from guillotina.schema.utils import make_binary
from guillotina.schema.vocabulary import getVocabularyRegistry
from guillotina.schema.vocabulary import SimpleVocabulary
from guillotina.schema.vocabulary import VocabularyRegistryError
from zope.interface import classImplements
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.interfaces import IInterface
from zope.interface.interfaces import IMethod

import decimal
import json
import jsonschema
import re


__docformat__ = 'restructuredtext'

# pep 8 friendlyness
Container

# Fix up bootstrap field types
Field.title = FieldProperty(IField['title'])
Field.description = FieldProperty(IField['description'])
Field.required = FieldProperty(IField['required'])
Field.readonly = FieldProperty(IField['readonly'])
# Default is already taken care of
classImplements(Field, IField)

MinMaxLen.min_length = FieldProperty(IMinMaxLen['min_length'])
MinMaxLen.max_length = FieldProperty(IMinMaxLen['max_length'])

classImplements(Text, IText)
classImplements(TextLine, ITextLine)
classImplements(Password, IPassword)
classImplements(Bool, IBool)
classImplements(Bool, IFromUnicode)
classImplements(Int, IInt)


@implementer(ISourceText)
class SourceText(Text):
    __doc__ = ISourceText.__doc__
    _type = str


@implementer(IBytes, IFromUnicode)
class Bytes(MinMaxLen, Field):
    __doc__ = IBytes.__doc__

    _type = bytes

    def from_unicode(self, uc):
        """ See IFromUnicode.
        """
        v = make_binary(uc)
        self.validate(v)
        return v


NativeString = Text


@implementer(IASCII)
class ASCII(NativeString):
    __doc__ = IASCII.__doc__

    def _validate(self, value):
        super(ASCII, self)._validate(value)
        if not value:
            return
        if not max(map(ord, value)) < 128:
            raise InvalidValue


@implementer(IBytesLine)
class BytesLine(Bytes):
    """A Text field with no newlines."""

    def constraint(self, value):
        # TODO: we should probably use a more general definition of newlines
        return b'\n' not in value


NativeStringLine = TextLine


@implementer(IASCIILine)
class ASCIILine(ASCII):
    __doc__ = IASCIILine.__doc__

    def constraint(self, value):
        # TODO: we should probably use a more general definition of newlines
        return '\n' not in value


@implementer(IFloat, IFromUnicode)
class Float(Orderable, Field):
    __doc__ = IFloat.__doc__
    _type = float

    def __init__(self, *args, **kw):
        super(Float, self).__init__(*args, **kw)

    def from_unicode(self, uc):
        """ See IFromUnicode.
        """
        v = float(uc)
        self.validate(v)
        return v


@implementer(IDecimal, IFromUnicode)
class Decimal(Orderable, Field):
    __doc__ = IDecimal.__doc__
    _type = decimal.Decimal

    def __init__(self, *args, **kw):
        super(Decimal, self).__init__(*args, **kw)

    def from_unicode(self, uc):
        """ See IFromUnicode.
        """
        try:
            v = decimal.Decimal(uc)
        except decimal.InvalidOperation:
            raise ValueError('invalid literal for Decimal(): %s' % uc)
        self.validate(v)
        return v


@implementer(IDatetime)
class Datetime(Orderable, Field):
    __doc__ = IDatetime.__doc__
    _type = datetime

    def __init__(self, *args, **kw):
        super(Datetime, self).__init__(*args, **kw)


@implementer(IDate)
class Date(Orderable, Field):
    __doc__ = IDate.__doc__
    _type = date

    def _validate(self, value):
        super(Date, self)._validate(value)
        if isinstance(value, datetime):
            raise WrongType(value, self._type, self.__name__)


@implementer(ITimedelta)
class Timedelta(Orderable, Field):
    __doc__ = ITimedelta.__doc__
    _type = timedelta


@implementer(ITime)
class Time(Orderable, Field):
    __doc__ = ITime.__doc__
    _type = time


@implementer(IChoice, IFromUnicode)
class Choice(Field):
    """Choice fields can have a value found in a constant or dynamic set of
    values given by the field definition.
    """

    def __init__(self, values=None, vocabulary=None, source=None, **kw):
        """Initialize object."""
        if vocabulary is not None:
            if (not isinstance(vocabulary, str) and
                    not IBaseVocabulary.providedBy(vocabulary)):
                raise ValueError('vocabulary must be a string or implement '
                                 'IBaseVocabulary')
            if source is not None:
                raise ValueError(
                    "You cannot specify both source and vocabulary.")
        elif source is not None:
            vocabulary = source

        if (values is None and vocabulary is None):
            raise ValueError(
                "You must specify either values or vocabulary."
            )
        if values is not None and vocabulary is not None:
            raise ValueError(
                "You cannot specify both values and vocabulary."
            )

        self.vocabulary = None
        self.vocabularyName = None
        if values is not None:
            self.vocabulary = SimpleVocabulary.fromValues(values)
        elif isinstance(vocabulary, str):
            self.vocabularyName = vocabulary
        else:
            if (not ISource.providedBy(vocabulary) and
                    not IContextSourceBinder.providedBy(vocabulary)):
                raise ValueError('Invalid vocabulary')
            self.vocabulary = vocabulary
        # Before a default value is checked, it is validated. However, a
        # named vocabulary is usually not complete when these fields are
        # initialized. Therefore signal the validation method to ignore
        # default value checks during initialization of a Choice tied to a
        # registered vocabulary.
        self._init_field = (bool(self.vocabularyName) or
                            IContextSourceBinder.providedBy(self.vocabulary))
        super(Choice, self).__init__(**kw)
        self._init_field = False

    source = property(lambda self: self.vocabulary)

    def bind(self, object):
        """See guillotina.schema._bootstrapinterfaces.IField."""
        clone = super(Choice, self).bind(object)
        # get registered vocabulary if needed:
        if IContextSourceBinder.providedBy(self.vocabulary):
            clone.vocabulary = self.vocabulary(object)
        elif clone.vocabulary is None and self.vocabularyName is not None:
            vr = getVocabularyRegistry()
            clone.vocabulary = vr.get(object, self.vocabularyName)

        if not ISource.providedBy(clone.vocabulary):
            raise ValueError('Invalid clone vocabulary')

        return clone

    def from_unicode(self, str):
        """ See IFromUnicode.
        """
        self.validate(str)
        return str

    def _validate(self, value):
        # Pass all validations during initialization
        if self._init_field:
            return
        super(Choice, self)._validate(value)
        vocabulary = self.vocabulary
        if vocabulary is None:
            vr = getVocabularyRegistry()
            try:
                vocabulary = vr.get(None, self.vocabularyName)
            except VocabularyRegistryError:
                raise ValueError("Can't validate value without vocabulary")
        if value not in vocabulary:
            raise ConstraintNotSatisfied(value, self.__name__)


_isuri = r"[a-zA-z0-9+.-]+:"  # scheme
_isuri += r"\S*$"  # non space (should be pickier)
_isuri = re.compile(_isuri).match


@implementer(IURI, IFromUnicode)
class URI(NativeStringLine):
    """URI schema field
    """

    def _validate(self, value):
        super(URI, self)._validate(value)
        if _isuri(value):
            return

        raise InvalidURI(value)

    def from_unicode(self, value):
        """ See IFromUnicode.
        """
        v = str(value.strip())
        self.validate(v)
        return v


_isdotted = re.compile(
    r"([a-zA-Z][a-zA-Z0-9_]*)"
    r"([.][a-zA-Z][a-zA-Z0-9_]*)*"
    # use the whole line
    r"$").match


@implementer(IDottedName)
class DottedName(NativeStringLine):
    """Dotted name field.

    Values of DottedName fields must be Python-style dotted names.
    """

    def __init__(self, *args, **kw):
        self.min_dots = int(kw.pop("min_dots", 0))
        if self.min_dots < 0:
            raise ValueError("min_dots cannot be less than zero")
        self.max_dots = kw.pop("max_dots", None)
        if self.max_dots is not None:
            self.max_dots = int(self.max_dots)
            if self.max_dots < self.min_dots:
                raise ValueError("max_dots cannot be less than min_dots")
        super(DottedName, self).__init__(*args, **kw)

    def _validate(self, value):
        """

        """
        super(DottedName, self)._validate(value)
        if not _isdotted(value):
            raise InvalidDottedName(value)
        dots = value.count(".")
        if dots < self.min_dots:
            raise InvalidDottedName(
                "too few dots; %d required" % self.min_dots, value
            )
        if self.max_dots is not None and dots > self.max_dots:
            raise InvalidDottedName("too many dots; no more than %d allowed" %
                                    self.max_dots, value)

    def from_unicode(self, value):
        v = value.strip()
        if not isinstance(v, self._type):
            v = v.encode('ascii')
        self.validate(v)
        return v


@implementer(IId, IFromUnicode)
class Id(NativeStringLine):
    """Id field

    Values of id fields must be either uris or dotted names.
    """

    def _validate(self, value):
        super(Id, self)._validate(value)
        if _isuri(value):
            return
        if _isdotted(value) and "." in value:
            return

        raise InvalidId(value)

    def from_unicode(self, value):
        """ See IFromUnicode.
        """
        v = value.strip()
        if not isinstance(v, self._type):
            v = v.encode('ascii')
        self.validate(v)
        return v


@implementer(IInterfaceField)
class InterfaceField(Field):
    __doc__ = IInterfaceField.__doc__

    def _validate(self, value):
        super(InterfaceField, self)._validate(value)
        if not IInterface.providedBy(value):
            raise WrongType("An interface is required", value, self.__name__)


def _validate_sequence(value_type, value, errors=None):
    """Validates a sequence value.

    Returns a list of validation errors generated during the validation. If
    no errors are generated, returns an empty list.

    value_type is a field. value is the sequence being validated. errors is
    an optional list of errors that will be prepended to the return value.

    To illustrate, we'll use a text value type. All values must be unicode.

       >>> field = TextLine(required=True)

    To validate a sequence of various values:

       >>> errors = _validate_sequence(field, (b'foo', 'bar', 1))
       >>> errors # XXX assumes Python2 reprs
       [WrongType('foo', <type 'unicode'>, ''), WrongType(1, <type 'unicode'>, '')]

    The only valid value in the sequence is the second item. The others
    generated errors.

    """
    if errors is None:
        errors = []
    if value_type is None:
        return errors
    for item in value:
        try:
            value_type.validate(item)
        except ValidationError as error:
            errors.append(error)
    return errors


def _validate_uniqueness(value):
    temp_values = []
    for item in value:
        if item in temp_values:
            raise NotUnique(item)

        temp_values.append(item)


class AbstractCollection(MinMaxLen, Iterable):
    value_type = None
    unique = False

    def __init__(self, value_type=None, unique=False, **kw):
        super(AbstractCollection, self).__init__(**kw)
        # whine if value_type is not a field
        if value_type is not None and not IField.providedBy(value_type):
            raise ValueError("'value_type' must be field instance.")
        self.value_type = value_type
        self.unique = unique

    def bind(self, object):
        """See guillotina.schema._bootstrapinterfaces.IField."""
        clone = super(AbstractCollection, self).bind(object)
        # binding value_type is necessary for choices with named vocabularies,
        # and possibly also for other fields.
        if clone.value_type is not None:
            clone.value_type = clone.value_type.bind(object)
        return clone

    def _validate(self, value):
        super(AbstractCollection, self)._validate(value)
        errors = _validate_sequence(self.value_type, value)
        if errors:
            raise WrongContainedType(errors, self.__name__)
        if self.unique:
            _validate_uniqueness(value)


@implementer(ITuple)
class Tuple(AbstractCollection):
    """A field representing a Tuple."""
    _type = tuple


@implementer(IList)
class List(AbstractCollection):
    """A field representing a List."""
    _type = list


@implementer(ISet)
class Set(AbstractCollection):
    """A field representing a set."""
    _type = set

    def __init__(self, **kw):
        if 'unique' in kw:  # set members are always unique
            raise TypeError(
                "__init__() got an unexpected keyword argument 'unique'")
        super(Set, self).__init__(unique=True, **kw)


@implementer(IFrozenSet)
class FrozenSet(AbstractCollection):
    _type = frozenset

    def __init__(self, **kw):
        if 'unique' in kw:  # set members are always unique
            raise TypeError(
                "__init__() got an unexpected keyword argument 'unique'")
        super(FrozenSet, self).__init__(unique=True, **kw)


VALIDATED_VALUES = {}


def _validate_fields(schema, value, errors=None):
    if errors is None:
        errors = []
    # Interface can be used as schema property for Object fields that plan to
    # hold values of any type.
    # Because Interface does not include any Attribute, it is obviously not
    # worth looping on its methods and filter them all out.
    if schema is Interface:
        return errors
    # if `value` is part of a cyclic graph, we need to break the cycle to avoid
    # infinite recursion. Collect validated objects in a thread local dict by
    # it's python represenation. A previous version was setting a volatile
    # attribute which didn't work with security proxy
    if id(value) in VALIDATED_VALUES:
        return errors
    VALIDATED_VALUES[id(value)] = True
    # (If we have gotten here, we know that `value` provides an interface
    # other than zope.interface.Interface;
    # iow, we can rely on the fact that it is an instance
    # that supports attribute assignment.)
    try:
        for name in schema.names(all=True):
            if not IMethod.providedBy(schema[name]):
                try:
                    attribute = schema[name]
                    if IChoice.providedBy(attribute):
                        # Choice must be bound before validation otherwise
                        # IContextSourceBinder is not iterable in validation
                        bound = attribute.bind(value)
                        bound.validate(getattr(value, name, None))
                    elif IField.providedBy(attribute):
                        # validate attributes that are fields
                        attribute.validate(getattr(value, name, None))
                except ValidationError as error:
                    errors.append(error)
                except AttributeError as error:
                    # property for the given name is not implemented
                    errors.append(SchemaNotFullyImplemented(error))
    finally:
        del VALIDATED_VALUES[id(value)]
    return errors


@implementer(IObject)
class Object(Field):
    __doc__ = IObject.__doc__

    def __init__(self, schema, **kw):
        if not IInterface.providedBy(schema):
            raise WrongType

        self.schema = schema
        super(Object, self).__init__(**kw)

    def _validate(self, value):
        super(Object, self)._validate(value)

        if isinstance(value, dict):
            # Dicts are validated differently
            valid_type = namedtuple(
                'temp_validate_type',
                set(self.schema.names()) & set(value.keys()))
            # check the value against schema
            errors = _validate_fields(self.schema, valid_type(**value))
        else:
            if not self.schema.providedBy(value):
                raise SchemaNotProvided
            errors = _validate_fields(self.schema, value)
        if errors:
            raise WrongContainedType(errors, self.__name__)

    def set(self, object, value):
        # Announce that we're going to assign the value to the object.
        # Motivation: Widgets typically like to take care of policy-specific
        # actions, like establishing location.
        event = BeforeObjectAssignedEvent(value, self.__name__, object)
        sync_notify(event)
        # The event subscribers are allowed to replace the object, thus we need
        # to replace our previous value.
        value = event.object
        super(Object, self).set(object, value)


@implementer(IBeforeObjectAssignedEvent)
class BeforeObjectAssignedEvent(object):
    """An object is going to be assigned to an attribute on another object."""

    def __init__(self, object, name, context):
        self.object = object
        self.name = name
        self.context = context


@implementer(IDict)
class Dict(MinMaxLen, Iterable):
    """A field representing a Dict."""
    _type = dict
    key_type = None
    value_type = None

    def __init__(self, key_type=None, value_type=None, **kw):
        super(Dict, self).__init__(**kw)
        # whine if key_type or value_type is not a field
        if key_type is not None and not IField.providedBy(key_type):
            raise ValueError("'key_type' must be field instance.")
        if value_type is not None and not IField.providedBy(value_type):
            raise ValueError("'value_type' must be field instance.")
        self.key_type = key_type
        self.value_type = value_type

    def _validate(self, value):
        super(Dict, self)._validate(value)
        errors = []
        try:
            if self.value_type:
                errors = _validate_sequence(self.value_type, value.values(),
                                            errors)
            errors = _validate_sequence(self.key_type, value, errors)

            if errors:
                raise WrongContainedType(errors, self.__name__)

        finally:
            errors = None

    def bind(self, object):
        """See guillotina.schema._bootstrapinterfaces.IField."""
        clone = super(Dict, self).bind(object)
        # binding value_type is necessary for choices with named vocabularies,
        # and possibly also for other fields.
        if clone.key_type is not None:
            clone.key_type = clone.key_type.bind(object)
        if clone.value_type is not None:
            clone.value_type = clone.value_type.bind(object)
        return clone


DEFAULT_JSON_SCHMEA = json.dumps({
    'type': 'object',
    'properties': {}
})


@implementer(IJSONField)
class JSONField(Field):

    def __init__(self, schema=DEFAULT_JSON_SCHMEA, **kw):
        if not isinstance(schema, str):
            raise WrongType

        try:
            self.json_schema = json.loads(schema)
        except ValueError:
            raise WrongType
        super(JSONField, self).__init__(**kw)

    def _validate(self, value):
        super(JSONField, self)._validate(value)

        try:
            jsonschema.validate(value, self.json_schema)
        except jsonschema.ValidationError as e:
            raise WrongContainedType(e.message, self.__name__)
