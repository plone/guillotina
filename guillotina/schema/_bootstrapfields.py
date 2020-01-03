##############################################################################
#
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
from guillotina.schema._bootstrapinterfaces import IContextAwareDefaultFactory
from guillotina.schema._bootstrapinterfaces import IFromUnicode
from guillotina.schema._schema import get_fields
from guillotina.schema.exceptions import ConstraintNotSatisfied
from guillotina.schema.exceptions import NotAContainer
from guillotina.schema.exceptions import NotAnIterator
from guillotina.schema.exceptions import RequiredMissing
from guillotina.schema.exceptions import StopValidation
from guillotina.schema.exceptions import TooBig
from guillotina.schema.exceptions import TooLong
from guillotina.schema.exceptions import TooShort
from guillotina.schema.exceptions import TooSmall
from guillotina.schema.exceptions import WrongType
from typing import Any
from zope.interface import Attribute
from zope.interface import implementer
from zope.interface import providedBy


__docformat__ = "restructuredtext"


class ValidatedProperty(object):
    def __init__(self, name, check=None):
        self._info = name, check

    def __set__(self, inst, value):
        name, check = self._info
        if value != inst.missing_value:
            if check is not None:
                check(inst, value)
            else:
                inst.validate(value)
        inst.__dict__[name] = value

    def __get__(self, inst, owner):
        name, check = self._info
        return inst.__dict__[name]


class DefaultProperty(ValidatedProperty):
    def __get__(self, inst, owner):
        name, check = self._info
        default_factory = inst.__dict__.get("defaultFactory")
        # If there is no default factory, simply return the default.
        if default_factory is None:
            return inst.__dict__[name]
        # Get the default value by calling the factory. Some factories might
        # require a context to produce a value.
        if IContextAwareDefaultFactory.providedBy(default_factory):
            value = default_factory(inst.context)
        else:
            value = default_factory()
        # Check that the created value is valid.
        if check is not None:
            check(inst, value)
        elif value != inst.missing_value:
            inst.validate(value)
        return value


class Field(Attribute):

    # Type restrictions, if any
    _type: Any = None
    context = None

    # If a field has no assigned value, it will be set to missing_value.
    missing_value = None

    # This is the default value for the missing_value argument to the
    # Field constructor.  A marker is helpful since we don't want to
    # overwrite missing_value if it is set differently on a Field
    # subclass and isn't specified via the constructor.
    __missing_value_marker = object()

    # Note that the "order" field has a dual existance:
    # 1. The class variable Field.order is used as a source for the
    #    monotonically increasing values used to provide...
    # 2. The instance variable self.order which provides a
    #    monotonically increasing value that tracks the creation order
    #    of Field (including Field subclass) instances.
    order = 0

    default = DefaultProperty("default")

    # These were declared as slots in zope.interface, we override them here to
    # get rid of the dedcriptors so they don't break .bind()
    __name__ = None
    interface = None
    _Element__tagged_values = None
    _validators = None

    def __init__(
        self,
        title="",
        description="",
        __name__="",
        required=None,
        readonly=False,
        constraint=None,
        default=None,
        defaultFactory=None,
        missing_value=__missing_value_marker,
        **kw,
    ):
        """Pass in field values as keyword parameters.


        Generally, you want to pass either a title and description, or
        a doc string.  If you pass no doc string, it will be computed
        from the title and description.  If you pass a doc string that
        follows the Python coding style (title line separated from the
        body by a blank line), the title and description will be
        computed from the doc string.  Unfortunately, the doc string
        must be passed as a positional argument.

        Here are some examples:

        >>> f = Field()
        >>> f.__doc__, f.title, f.description
        ('', u'', u'')

        >>> f = Field(title='sample')
        >>> f.__doc__, f.title, f.description
        (u'sample', u'sample', u'')

        >>> f = Field(title='sample', description='blah blah\\nblah')
        >>> f.__doc__, f.title, f.description
        (u'sample\\n\\nblah blah\\nblah', u'sample', u'blah blah\\nblah')
        """
        __doc__ = ""
        if title:
            if description:
                __doc__ = "%s\n\n%s" % (title, description)
            else:
                __doc__ = title
        elif description:
            __doc__ = description

        super(Field, self).__init__(__name__, __doc__)
        self.title = title
        self.description = description
        if required is not None:
            self.required = required
        self.readonly = readonly
        if constraint is not None:
            self.constraint = constraint
        self.default = default
        self.defaultFactory = defaultFactory

        # Keep track of the order of field definitions
        Field.order += 1
        self.order = Field.order

        self.extra_values = kw

        if missing_value is not self.__missing_value_marker:
            self.missing_value = missing_value

    def validator(self, func):
        if self._validators is None:
            self._validators = []
        self._validators.append(func)
        return func

    def constraint(self, value):  # type: ignore
        return True

    def bind(self, object):
        clone = self.__class__.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone.context = object
        return clone

    def validate(self, value):
        if value == self.missing_value:
            if self.required:
                raise RequiredMissing(self.__name__)
        else:
            try:
                self._validate(value)
            except StopValidation:
                pass

    def __eq__(self, other):
        # should be the same type
        if type(self) != type(other):
            return False

        # should have the same properties
        names = {}  # used as set of property names, ignoring values
        for interface in providedBy(self):
            names.update(get_fields(interface))

        # order will be different always, don't compare it
        if "order" in names:
            del names["order"]
        for name in names:
            if getattr(self, name) != getattr(other, name):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def _validate(self, value):
        if self._type is not None and not isinstance(value, self._type):
            raise WrongType(value, self._type, self.__name__)

        if not self.constraint(value):
            raise ConstraintNotSatisfied(value, self.__name__)
        for validator in self._validators or []:
            validator(self, value)

    def get(self, object):
        return getattr(object, self.__name__)

    def query(self, object, default=None):
        return getattr(object, self.__name__, default)

    def set(self, object, value):
        if self.readonly:
            raise TypeError(
                "Can't set values on read-only fields "
                "(name=%s, class=%s.%s)"
                % (self.__name__, object.__class__.__module__, object.__class__.__name__)
            )
        setattr(object, self.__name__, value)


class Container(Field):
    def _validate(self, value):
        super(Container, self)._validate(value)

        if not hasattr(value, "__contains__"):
            try:
                iter(value)
            except TypeError:
                raise NotAContainer(value)


# XXX This class violates the Liskov Substituability Principle:  it
#     is derived from Container, but cannot be used everywhere an instance
#     of Container could be, because it's '_validate' is more restrictive.
class Iterable(Container):
    def _validate(self, value):
        super(Iterable, self)._validate(value)

        # See if we can get an iterator for it
        try:
            iter(value)
        except TypeError:
            raise NotAnIterator(value)


class Orderable(object):
    """Values of ordered fields can be sorted.

    They can be restricted to a range of values.

    Orderable is a mixin used in combination with Field.
    """

    min = ValidatedProperty("min")
    max = ValidatedProperty("max")

    def __init__(self, min=None, max=None, default=None, **kw):

        # Set min and max to None so that we can validate if
        # one of the super methods invoke validation.
        self.min = None
        self.max = None

        super(Orderable, self).__init__(**kw)

        # Now really set min and max
        self.min = min
        self.max = max

        # We've taken over setting default so it can be limited by min
        # and max.
        self.default = default

    def _validate(self, value):
        super(Orderable, self)._validate(value)

        if self.min is not None and value < self.min:
            raise TooSmall(value, self.min)

        if self.max is not None and value > self.max:
            raise TooBig(value, self.max)


class MinMaxLen(object):
    """Expresses constraints on the length of a field.

    MinMaxLen is a mixin used in combination with Field.
    """

    min_length = 0
    max_length = None

    def __init__(self, min_length=0, max_length=None, **kw):
        self.min_length = min_length
        self.max_length = max_length
        super(MinMaxLen, self).__init__(**kw)

    def _validate(self, value):
        super(MinMaxLen, self)._validate(value)

        if self.min_length is not None and len(value) < self.min_length:
            raise TooShort(value, self.min_length)

        if self.max_length is not None and len(value) > self.max_length:
            raise TooLong(value, self.max_length)


@implementer(IFromUnicode)
class Text(MinMaxLen, Field):
    """A field containing text used for human discourse."""

    _type = str

    def __init__(self, *args, **kw):
        super(Text, self).__init__(*args, **kw)

    def from_unicode(self, str):
        """
        >>> t = Text(constraint=lambda v: 'x' in v)
        >>> t.from_unicode(b"foo x spam")
        Traceback (most recent call last):
        ...
        WrongType: ('foo x spam', <type 'unicode'>, '')
        >>> t.from_unicode("foo x spam")
        u'foo x spam'
        >>> t.from_unicode("foo spam")
        Traceback (most recent call last):
        ...
        ConstraintNotSatisfied: ('foo spam', '')
        """
        self.validate(str)
        return str


class TextLine(Text):
    """A text field with no newlines."""

    def constraint(self, value):
        return "\n" not in value and "\r" not in value


class Password(TextLine):
    """A text field containing a text used as a password."""

    UNCHANGED_PASSWORD = object()

    def set(self, context, value):
        """Update the password.

        We use a special marker value that a widget can use
        to tell us that the password didn't change. This is
        needed to support edit forms that don't display the
        existing password and want to work together with
        encryption.

        """
        if value is self.UNCHANGED_PASSWORD:
            return
        super(Password, self).set(context, value)

    def validate(self, value):
        try:
            existing = bool(self.get(self.context))
        except AttributeError:
            existing = False
        if value is self.UNCHANGED_PASSWORD and existing:
            # Allow the UNCHANGED_PASSWORD value, if a password is set already
            return
        return super(Password, self).validate(value)


class Bool(Field):
    """A field representing a Bool."""

    _type = bool

    def _validate(self, value):
        # Convert integers to bools to they don't get mis-flagged
        # by the type check later.
        if isinstance(value, int):
            value = bool(value)
        Field._validate(self, value)

    def set(self, object, value):
        if isinstance(value, int):
            value = bool(value)
        Field.set(self, object, value)

    def from_unicode(self, str):
        """
        >>> b = Bool()
        >>> IFromUnicode.providedBy(b)
        True
        >>> b.from_unicode('True')
        True
        >>> b.from_unicode('')
        False
        >>> b.from_unicode('true')
        True
        >>> b.from_unicode('false') or b.from_unicode('False')
        False
        """
        v = str == "True" or str == "true"
        self.validate(v)
        return v


@implementer(IFromUnicode)
class Int(Orderable, Field):
    """A field representing an Integer."""

    _type = int

    def __init__(self, *args, **kw):
        super(Int, self).__init__(*args, **kw)

    def from_unicode(self, str):
        """
        >>> f = Int()
        >>> f.from_unicode("125")
        125
        >>> f.from_unicode("125.6") #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ...
        ValueError: invalid literal for int(): 125.6
        """
        v = int(str)
        self.validate(v)
        return v
