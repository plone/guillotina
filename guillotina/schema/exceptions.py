from guillotina.schema._messageid import _

import zope.interface


class StopValidation(Exception):
    """Raised if the validation is completed early.

    Note that this exception should be always caught, since it is just
    a way for the validator to save time.
    """


class ValidationError(zope.interface.Invalid):
    """Raised if the Validation process fails."""

    def __init__(self, value=None, type=None, field_name="", errors=None, constraint=None):
        super().__init__(value, type, field_name)
        self.value = value
        self.type = type
        self.field_name = field_name
        self.errors = errors
        self.constraint = constraint

    def doc(self):
        if self.value and self.type:
            return f"Expected {self.type} but found {type(self.value)}."
        return self.__class__.__doc__

    def json(self):
        d = {
            "message": self.doc(),
            "error": self,
        }
        if self.field_name:
            d["field"] = self.field_name
        if self.value:
            if type(self.value) in (str, int, float):
                d["value"] = self.value
            else:
                d["value"] = repr(self.value)
        return d

    def __eq__(self, other):
        if not hasattr(other, "args"):
            return False
        return self.args == other.args

    __hash__ = zope.interface.Invalid.__hash__  # python3

    def __repr__(self):  # pragma: no cover
        return "%s(%s)" % (self.__class__.__name__, ", ".join(repr(arg) for arg in self.args))


class RequiredMissing(ValidationError):
    __doc__ = _("""Required input is missing.""")

    def __init__(self, field_name):
        super().__init__(field_name=field_name)


class WrongType(ValidationError):
    __doc__ = _("""Object is of wrong type.""")

    def __init__(self, value, type, field_name):
        super().__init__(value=value, type=type, field_name=field_name)


class TooBig(ValidationError):
    __doc__ = _("""Value is too big""")

    def __init__(self, value, constraint, field_name=""):
        super().__init__(value=value, constraint=constraint, field_name=field_name)


class TooSmall(ValidationError):
    __doc__ = _("""Value is too small""")

    def __init__(self, value, constraint, field_name=""):
        super().__init__(value=value, constraint=constraint, field_name=field_name)


class TooLong(ValidationError):
    __doc__ = _("""Value is too long""")

    def __init__(self, value, constraint, field_name=""):
        super().__init__(value=value, constraint=constraint, field_name=field_name)


class TooShort(ValidationError):
    __doc__ = _("""Value is too short""")

    def __init__(self, value, constraint, field_name=""):
        super().__init__(value=value, constraint=constraint, field_name=field_name)


class InvalidValue(ValidationError):
    __doc__ = _("""Invalid value""")

    def __init__(self, value, field_name):
        super().__init__(value=value, field_name=field_name)


class ConstraintNotSatisfied(ValidationError):
    __doc__ = _("""Constraint not satisfied""")

    def __init__(self, value, field_name):
        super().__init__(value=value, field_name=field_name)


class NotAContainer(ValidationError):
    __doc__ = _("""Not a container""")

    def __init__(self, value):
        super().__init__(value=value)


class NotAnIterator(ValidationError):
    __doc__ = _("""Not an iterator""")

    def __init__(self, value):
        super().__init__(value=value)


class WrongContainedType(ValidationError):
    __doc__ = _("""Wrong contained type""")

    def __init__(self, errors, field_name, value=None):
        super().__init__(value=value, field_name=field_name, errors=errors)


class NotUnique(ValidationError):
    __doc__ = _("""One or more entries of sequence are not unique.""")


class SchemaNotFullyImplemented(ValidationError):
    __doc__ = _("""Schema not fully implemented""")


class SchemaNotProvided(ValidationError):
    __doc__ = _("""Schema not provided""")

    def __init__(self, value, field_name):
        super().__init__(value=value, field_name=field_name)


class InvalidURI(ValidationError):
    __doc__ = _("""The specified URI is not valid.""")


class InvalidId(ValidationError):
    __doc__ = _("""The specified id is not valid.""")


class InvalidDottedName(ValidationError):
    __doc__ = _("""The specified dotted name is not valid.""")


class Unbound(Exception):
    __doc__ = _("""The field is not bound.""")
