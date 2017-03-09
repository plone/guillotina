from guillotina.schema._messageid import _

import zope.interface


class StopValidation(Exception):
    """Raised if the validation is completed early.

    Note that this exception should be always caught, since it is just
    a way for the validator to save time.
    """


class ValidationError(zope.interface.Invalid):
    """Raised if the Validation process fails."""

    def doc(self):
        return self.__class__.__doc__

    def __eq__(self, other):
        if not hasattr(other, 'args'):
            return False
        return self.args == other.args

    __hash__ = zope.interface.Invalid.__hash__  # python3

    def __repr__(self):  # pragma: no cover
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join(repr(arg) for arg in self.args))


class RequiredMissing(ValidationError):
    __doc__ = _("""Required input is missing.""")


class WrongType(ValidationError):
    __doc__ = _("""Object is of wrong type.""")


class TooBig(ValidationError):
    __doc__ = _("""Value is too big""")


class TooSmall(ValidationError):
    __doc__ = _("""Value is too small""")


class TooLong(ValidationError):
    __doc__ = _("""Value is too long""")


class TooShort(ValidationError):
    __doc__ = _("""Value is too short""")


class InvalidValue(ValidationError):
    __doc__ = _("""Invalid value""")


class ConstraintNotSatisfied(ValidationError):
    __doc__ = _("""Constraint not satisfied""")


class NotAContainer(ValidationError):
    __doc__ = _("""Not a container""")


class NotAnIterator(ValidationError):
    __doc__ = _("""Not an iterator""")


class WrongContainedType(ValidationError):
    __doc__ = _("""Wrong contained type""")


class NotUnique(ValidationError):
    __doc__ = _("""One or more entries of sequence are not unique.""")


class SchemaNotFullyImplemented(ValidationError):
    __doc__ = _("""Schema not fully implemented""")


class SchemaNotProvided(ValidationError):
    __doc__ = _("""Schema not provided""")


class InvalidURI(ValidationError):
    __doc__ = _("""The specified URI is not valid.""")


class InvalidId(ValidationError):
    __doc__ = _("""The specified id is not valid.""")


class InvalidDottedName(ValidationError):
    __doc__ = _("""The specified dotted name is not valid.""")


class Unbound(Exception):
    __doc__ = _("""The field is not bound.""")
