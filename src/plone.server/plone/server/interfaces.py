# -*- coding: utf-8 -*-
from zope.component.interfaces import ISite
from zope.interface import Interface, Attribute
from zope.interface import interfaces
from plone.supermodel import model
from zope.schema.interfaces import IObject
from zope import schema

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
    """ Interface to create uploaders and downloaders
    """

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
    """Field for storing IFile objects.
    """


class IStorage(Interface):
    """Store file data
    """

    def store(data, blob):
        """Store the data into the blob
        Raises NonStorable if data is not storable.
        """


class NotStorable(Exception):
    """Data is not storable
    """



# Specific Events


class IObjectFinallyCreatedEvent(interfaces.IObjectEvent):
    """An object has been created.

    The location will usually be ``None`` for this event."""


class INewUserAdded(Interface):
    """A new user logged in.

    The user is the id from the user logged in"""

    user = Attribute("User id created.")


