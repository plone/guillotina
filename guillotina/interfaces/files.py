from guillotina import schema
from guillotina.directives import index
from guillotina.directives import metadata
from guillotina.schema.interfaces import IObject
from zope.interface import Interface


class IFileManager(Interface):
    """Interface to create uploaders and downloaders."""

    async def upload(self):
        '''
        '''

    async def download(self):
        '''
        '''

    async def tus_post(self):
        '''
        '''

    async def tus_patch(self):
        '''
        '''

    async def tus_options(self):
        '''
        '''

    async def tus_head(self):
        '''
        '''


class IFileCleanup(Interface):

    def __init__(context):
        '''
        adapter of ob file is on
        '''

    def should_clean(**kwargs):
        '''
        whether or not old file should be cleaned
        '''


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
        default='',
        required=False)

    index('md5', type='text')
    md5 = schema.TextLine(
        title='MD5',
        default='',
        required=False)

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


class IDBFileField(ICloudFileField):
    '''
    Store files in database blob storage
    '''


class IDBFile(IFile):
    """Marker for a DBFile
    """
