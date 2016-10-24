# -*- coding: utf-8 -*-
from plone.supermodel import model
from zope import schema
from zope.component.interfaces import ISite
from zope.i18nmessageid.message import MessageFactory
from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import interfaces
from zope.schema.interfaces import IObject


_ = MessageFactory('plone.server')

DEFAULT_READ_PERMISSION = 'plone.ViewContent'
DEFAULT_WRITE_PERMISSION = 'plone.ManageContent'


class IApplication(Interface):
    pass


class IDataBase(Interface):
    pass


class IStaticFile(Interface):
    pass


class IStaticDirectory(Interface):
    pass


class IPloneSite(model.Schema, ISite):
    title = schema.TextLine(
        title='Title',
        required=False,
        description=u"Title of the Site",
        default=u''
    )


class IItem(model.Schema):
    pass


class IContentNegotiation(Interface):
    pass


class IRequest(Interface):
    pass


class IResponse(Interface):

    def __init__(context, request):
        pass


class IView(Interface):

    def __init__(context, request):
        pass

    async def __call__(self):
        pass


class ITraversableView(IView):

    def publishTraverse(traverse_to):
        pass


class IDownloadView(IView):
    pass


class IGET(IView):
    pass


class IPUT(IView):
    pass


class IPOST(IView):
    pass


class IPATCH(IView):
    pass


class IDELETE(IView):
    pass


class IOPTIONS(IView):
    pass


class IHEAD(IView):
    pass


class ICONNECT(IView):
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

# File related interface


class IFileManager(Interface):
    """Interface to create uploaders and downloaders."""

    async def upload(self):
        pass

    async def download(self):
        pass

    async def tus_post(self):
        pass

    async def tus_patch(self):
        pass

    async def tus_options(self):
        pass

    async def tus_head(self):
        pass


class IFile(Interface):

    contentType = schema.BytesLine(
        title=u'Content Type',
        description=u'The content type identifies the type of data.',
        default=b'',
        required=False
    )

    filename = schema.TextLine(title=u'Filename', required=False, default=None)

    data = schema.Bytes(
        title=u'Data',
        description=u'The actual content.',
        required=False,
    )

    def getSize():
        """Return the byte-size of the data of the object."""


# File Field

class IFileField(IObject):
    """Field for storing IFile objects."""


class IStorage(Interface):
    """Store file data."""

    def store(data, blob):
        """Store the data into the blob
        Raises NonStorable if data is not storable.
        """


class NotStorable(Exception):
    """Data is not storable."""


# Text field

class IRichText(IObject):
    """A text field that stores MIME type
    """

    default_mime_type = schema.ASCIILine(
        title=_(u"Default MIME type"),
        default='text/html',
    )

    output_mime_type = schema.ASCIILine(
        title=_(u"Default output MIME type"),
        default='text/x-html-safe'
    )

    allowed_mime_types = schema.Tuple(
        title=_(u"Allowed MIME types"),
        description=_(u"Set to None to disable checking"),
        default=None,
        required=False,
        value_type=schema.ASCIILine(title=u"MIME type"),
    )

    max_length = schema.Int(
        title=_(u'Maximum length'),
        description=_(u'in characters'),
        required=False,
        min=0,
        default=None,
    )


class IRichTextValue(Interface):
    """The value actually stored in a RichText field.
    This stores the following values on the parent object
      - A separate persistent object with the original value
      - A cache of the value transformed to the default output type
    The object is immutable.
    """

    raw = schema.Text(
        title=_(u"Raw value in the original MIME type"),
        readonly=True,
    )

    mimeType = schema.ASCIILine(
        title=_(u"MIME type"),
        readonly=True,
    )

    outputMimeType = schema.ASCIILine(
        title=_(u"Default output MIME type"),
        readonly=True,
    )

    encoding = schema.ASCIILine(
        title=_(u"Default encoding for the value"),
        description=_(u"Mainly used internally"),
        readonly=True,
    )

    raw_encoded = schema.ASCII(
        title=_(u"Get the raw value as an encoded string"),
        description=_(u"Mainly used internally"),
        readonly=True,
    )

    output = schema.Text(
        title=_(u"Transformed value in the target MIME type"),
        description=_(u"May be None if the transform cannot be completed"),
        readonly=True,
        required=False,
        missing_value=None,
    )


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


# Specific Events


class IObjectFinallyCreatedEvent(interfaces.IObjectEvent):
    """An object has been created.

    The location will usually be ``None`` for this event."""


class INewUserAdded(Interface):
    """A new user logged in.

    The user is the id from the user logged in"""

    user = Attribute("User id created.")
