# -*- coding: utf-8 -*-
from plone.server.interfaces.catalog import ICatalogDataAdapter  # noqa
from plone.server.interfaces.catalog import ICatalogUtility  # noqa
from plone.server.interfaces.content import IApplication  # noqa
from plone.server.interfaces.content import IContainer  # noqa
from plone.server.interfaces.content import IContentNegotiation  # noqa
from plone.server.interfaces.content import IDatabase  # noqa
from plone.server.interfaces.content import IItem  # noqa
from plone.server.interfaces.content import IRegistry  # noqa
from plone.server.interfaces.content import IResource  # noqa
from plone.server.interfaces.content import IResourceFactory  # noqa
from plone.server.interfaces.content import ISite  # noqa
from plone.server.interfaces.content import IStaticDirectory  # noqa
from plone.server.interfaces.content import IStaticFile  # noqa
from plone.server.interfaces.events import INewUserAdded  # noqa
from plone.server.interfaces.events import IObjectFinallyCreatedEvent  # noqa
from plone.server.interfaces.events import IObjectFinallyDeletedEvent  # noqa
from plone.server.interfaces.events import IObjectFinallyModifiedEvent  # noqa
from plone.server.interfaces.exceptions import ISerializableException  # noqa
from plone.server.interfaces.events import IObjectFinallyVisitedEvent  # noqa
from plone.server.interfaces.events import IObjectPermissionsViewEvent  # noqa
from plone.server.interfaces.events import IObjectPermissionsModifiedEvent  # noqa
from plone.server.interfaces.events import IFileFinishUploaded  # noqa
from plone.server.interfaces.files import IFile  # noqa
from plone.server.interfaces.files import IFileField  # noqa
from plone.server.interfaces.files import IFileManager  # noqa
from plone.server.interfaces.files import IStorage  # noqa
from plone.server.interfaces.files import NotStorable  # noqa
from plone.server.interfaces.json import IJSONField  # noqa
from plone.server.interfaces.json import IBeforeJSONAssignedEvent  # noqa
from plone.server.interfaces.text import IRichText  # noqa
from plone.server.interfaces.text import IRichTextValue  # noqa
from plone.server.interfaces.types import IConstrainTypes  # noqa
from plone.server.interfaces.views import ICONNECT  # noqa
from plone.server.interfaces.views import IDELETE  # noqa
from plone.server.interfaces.views import IDownloadView  # noqa
from plone.server.interfaces.views import IGET  # noqa
from plone.server.interfaces.views import IHEAD  # noqa
from plone.server.interfaces.views import IOPTIONS  # noqa
from plone.server.interfaces.views import IPATCH  # noqa
from plone.server.interfaces.views import IPOST  # noqa
from plone.server.interfaces.views import IPUT  # noqa
from plone.server.interfaces.views import ITraversableView  # noqa
from plone.server.interfaces.views import IView  # noqa
from zope.i18nmessageid.message import MessageFactory
from zope.interface import Interface


_ = MessageFactory('plone.server')

DEFAULT_ADD_PERMISSION = 'plone.AddContent'
DEFAULT_READ_PERMISSION = 'plone.ViewContent'
DEFAULT_WRITE_PERMISSION = 'plone.ManageContent'

SHARED_CONNECTION = False
WRITING_VERBS = ['POST', 'PUT', 'PATCH', 'DELETE']
SUBREQUEST_METHODS = ['get', 'delete', 'head', 'options', 'patch', 'put']


class IFormFieldProvider(Interface):
    """Marker interface for schemata that provide form fields.
    """


class IRequest(Interface):
    pass


class IResponse(Interface):

    def __init__(context, request):
        pass


# Classes as for marker objects to lookup


class IRenderFormats(Interface):
    pass


class IFrameFormats(Interface):
    pass


class ILanguage(Interface):
    pass


# Target interfaces on resolving

class IRendered(Interface):
    pass


class ITranslated(Interface):
    pass

# Get Absolute URL


class IAbsoluteURL(Interface):
    pass


# Addon interface

class IAddOn(Interface):

    def install(self, site):
        pass

    def uninstall(self):
        pass


class TransformError(Exception):
    """Exception raised if a value could not be transformed. This is normally
    caused by another exception. Inspect self.cause to find that.
    """

    def __init__(self, message, cause=None):
        self.message = message
        self.cause = cause

    def __str__(self):
        return self.message


class ITransformer(Interface):
    """A simple abstraction for invoking a transformation from one MIME
    type to another.
    This is not intended as a general transformations framework, but rather
    as a way to abstract away a dependency on the underlying transformation
    engine.
    This interface will be implemented by an adapter onto the context where
    the value is stored.
    """

    def __init__(object):
        """Set the value object."""

    def __call__():
        """Transform the IRichTextValue 'value' to the given MIME type.
        Return a unicode string. Raises TransformError if something went
        wrong.
        """
