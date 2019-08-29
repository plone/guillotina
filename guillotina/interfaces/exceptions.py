from zope.interface import Interface
from zope.interface.common.interfaces import IException


class IUnauthorized(IException):
    """
    """


class IErrorResponseException(Interface):
    """
    Provide response object for uncaught exceptions
    """
