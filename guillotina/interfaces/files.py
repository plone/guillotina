from guillotina import schema
from guillotina.directives import index
from guillotina.directives import metadata
from guillotina.schema.interfaces import IObject
from zope.interface import Interface


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

    metadata('extension', 'md5', 'content_type', 'filename')

    index('content_type', type='text')
    content_type = schema.BytesLine(
        title=u'Content Type',
        description=u'The content type identifies the type of data.',
        default=b'',
        required=False
    )

    index('filename', type='text')
    filename = schema.TextLine(title=u'Filename', required=False, default=None)

    data = schema.Bytes(
        title=u'Data',
        description=u'The actual content.',
        required=False,
    )

    index('extension', type='text')
    extension = schema.TextLine(
        title='Extension of the file',
        default='')

    index('md5', type='text')
    md5 = schema.TextLine(
        title='MD5',
        default='')

    size = schema.Int(
        title='Size',
        default=0)

    def get_size():
        """Return the byte-size of the data of the object."""


# File Field

class IFileField(IObject):
    """Field for storing IFile objects."""


class ICloudFileField(IObject):
    """Field for storing generic cloud File objects."""


class IStorage(Interface):
    """Store file data."""

    def store(data, blob):
        """Store the data into the blob
        Raises NonStorable if data is not storable.
        """


class NotStorable(Exception):
    """Data is not storable."""
