from guillotina import schema
from guillotina.schema.interfaces import IObject
from zope.interface import Interface


class IUploadDataManager(Interface):
    '''
    Interface to manage upload data
    '''

    async def load():
        '''
        Load the current upload status
        '''

    async def update(**kwargs):
        '''
        update file upload data
        '''

    async def finish():
        '''
        finish upload
        '''

    async def save():
        '''
        save any current operations to db
        '''

    async def get(name):
        '''
        get attribute
        '''

    async def get_offset(self):
        '''
        get current upload offset
        '''


class IFileStorageManager(Interface):
    '''
    Manage storing file data
    '''

    async def start(dm):
        '''
        start upload
        '''

    async def iter_data():
        '''
        iterate through data in file
        '''

    async def append(data):
        '''
        append data to the file
        '''

    async def finish():
        '''
        finish upload
        '''

    async def copy(dm, other_storage_manager, other_dm):
        '''
        copy file to another file
        '''


class IFileManager(Interface):
    """Interface to create uploaders and downloaders."""

    async def upload():
        '''
        Upload complete file in one shot
        '''

    async def download():
        '''
        Download file
        '''

    async def tus_post():
        '''
        Start tus upload process
        '''

    async def tus_patch():
        '''
        Upload part of file
        '''

    async def tus_options():
        '''
        Get tus supported version
        '''

    async def tus_head():
        '''
        Get current tus status
        '''

    async def iter_data():
        '''
        Return an async iterator of the file
        '''

    async def save_file(generator):
        '''
        Save data to a file from an async generator
        '''

    async def copy(other_manager):
        '''
        Copy current file to new one
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

    content_type = schema.TextLine(
        title=u'Content Type',
        description=u'The content type identifies the type of data.',
        default='',
        required=False
    )

    filename = schema.TextLine(title=u'Filename', required=False, default=None)

    extension = schema.TextLine(
        title='Extension of the file',
        default='',
        required=False)

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
