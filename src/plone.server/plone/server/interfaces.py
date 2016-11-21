# -*- coding: utf-8 -*-
from zope import schema
from zope.component.interfaces import ISite as IZopeSite
from zope.component.interfaces import IFactory
from zope.i18nmessageid.message import MessageFactory
from zope.interface import Attribute
from zope.interface import Interface
from zope.interface import interfaces
from zope.interface.common.mapping import IFullMapping
from zope.location.interfaces import IContained
from zope.schema.interfaces import IObject

import zope.schema


_ = MessageFactory('plone.server')

DEFAULT_ADD_PERMISSION = 'plone.AddContent'
DEFAULT_READ_PERMISSION = 'plone.ViewContent'
DEFAULT_WRITE_PERMISSION = 'plone.ManageContent'

CATALOG_KEY = 'plone.server.directives.catalog'
FIELDSETS_KEY = 'plone.server.directives.fieldsets'
INDEX_KEY = 'plone.server.directives.index'
READ_PERMISSIONS_KEY = 'plone.server.directives.read-permissions'
WRITE_PERMISSIONS_KEY = 'plone.server.directives.write-permissions'

SHARED_CONNECTION = False
WRITING_VERBS = ['POST', 'PUT', 'PATCH', 'DELETE']
SUBREQUEST_METHODS = ['get', 'delete', 'head', 'options', 'patch', 'put']


class IFormFieldProvider(Interface):
    """Marker interface for schemata that provide form fields.
    """


class IApplication(Interface):
    pass


class IDataBase(Interface):
    pass


class IStaticFile(Interface):
    pass


class IStaticDirectory(Interface):
    pass


class IRegistry(IFullMapping):

    def forInterface(interface, check=True, omit=(), prefix=None):
        """Get an IRecordsProxy for the given interface. If `check` is True,
        an error will be raised if one or more fields in the interface does
        not have an equivalent setting.
        """

    def registerInterface(interface, omit=(), prefix=None):
        """Create a set of records based on the given interface. For each
        schema field in the interface, a record will be inserted with a
        name like `${interface.__identifier__}.${field.__name__}`, and a
        value equal to default value of that field. Any field with a name
        listed in `omit`, or with the `readonly` property set to True, will
        be ignored. Supply an alternative identifier with `prefix`.
        """


class IResource(IContained):
    portal_type = schema.TextLine()

    title = schema.TextLine(
        title='Title',
        required=False,
        description=u"Title of the Site",
        default=u''
    )


class IResourceFactory(IFactory):

    portal_type = schema.TextLine(
        title='Portal type name',
        description='The portal type this is an FTI for'
    )

    schema = schema.DottedName(
        title='Schema interface',
        description='Dotted name to an interface describing the type. '
                    'This is not required if there is a model file or a '
                    'model source string containing an unnamed schema.'
    )

    behaviors = zope.schema.List(
        title='Behaviors',
        description='A list of behaviors that are enabled for this type. '
                    'See plone.behavior for more details.',
        value_type=zope.schema.DottedName(title='Behavior name')
    )

    add_permission = zope.schema.DottedName(
        title='Add permission',
        description='A oermission name for the permission required to '
                    'construct this content',
    )


class ISite(IResource, IZopeSite):
    pass


class IItem(IResource):
    pass


class IContainer(IResource, IFullMapping):
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
