from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.files.utils import convert_base64_to_binary
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IContentBehavior
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IValueToJson
from guillotina.schema import Object
from guillotina.schema.fieldproperty import FieldProperty
from guillotina.utils import get_content_path
from guillotina.utils import to_str
from zope.interface import implementer

import mimetypes
import uuid


@implementer(ICloudFileField)
class CloudFileField(Object):
    """
    A cloud file hosted file.

    Its configured on config.json with :

    "cloud_storage": "guillotina.interfaces.IS3FileField"

    or

    "cloud_storage": "guillotina_gcloudstorage.interfaces.IGCloudFileField"

    """

    schema = IFile

    def __init__(self, **kw):
        super(CloudFileField, self).__init__(schema=self.schema, **kw)


@configure.adapter(for_=IFile, provides=IValueToJson)
def json_converter(value):
    if value is None:
        return value

    return {
        'filename': value.filename,
        'content_type': to_str(value.content_type),
        'size': value.size,
        'extension': value.extension,
        'md5': value.md5
    }


@implementer(IFile)
class BaseCloudFile:
    """Base cloud file storage class"""

    filename = FieldProperty(IFile['filename'])
    valid = True

    def __init__(self, content_type='application/octet-stream',
                 filename=None, size=0, md5=None):
        if not isinstance(content_type, bytes):
            content_type = content_type.encode('utf8')
        self.content_type = content_type
        if filename is not None:
            self.filename = filename
            extension_discovery = filename.split('.')
            if len(extension_discovery) > 1:
                self._extension = extension_discovery[-1]
        elif self.filename is None:
            self.filename = uuid.uuid4().hex

        self._size = size
        self._md5 = md5
        self._data = b''

    def guess_content_type(self):
        ct = to_str(self.content_type)
        if ct == 'application/octet-stream':
            # try guessing content_type
            ct, _ = mimetypes.guess_type(self.filename)
            if ct is None:
                ct = 'application/octet-stream'
        return ct

    def generate_key(self, request, context):
        return '{}{}/{}::{}'.format(
            request._container_id,
            get_content_path(context),
            context._p_oid,
            uuid.uuid4().hex)

    def get_actual_size(self):
        return self._current_upload

    def _set_data(self, data):
        self._data = data

    def _get_data(self):
        return self._data

    data = property(_get_data, _set_data)

    @property
    def uri(self):
        if hasattr(self, '_uri'):
            return self._uri

    @property
    def size(self):
        if hasattr(self, '_size'):
            return self._size
        else:
            return None

    @property
    def md5(self):
        if hasattr(self, '_md5'):
            return self._md5
        else:
            return None

    @property
    def extension(self):
        if hasattr(self, '_extension'):
            return self._extension
        else:
            return None

    async def copy_cloud_file(self, new_uri):
        raise NotImplemented()

    async def rename_cloud_file(self, new_uri):
        raise NotImplemented()

    async def init_upload(self, context):
        raise NotImplemented()

    async def append_data(self, data):
        raise NotImplemented()

    async def finish_upload(self, context):
        raise NotImplemented()

    async def delete_upload(self, uri=None):
        raise NotImplemented()

    async def download(self, buf):
        raise NotImplemented()


@configure.adapter(
    for_=(str, ICloudFileField),
    provides=IJSONToValue)
class CloudFileStrDeserializeValue:

    def __init__(self, value, field):
        self.value = convert_base64_to_binary(value)
        self.field = field

    async def generator(self):
        yield self.value['data']

    async def __call__(self, context, request):
        if IContentBehavior.implementedBy(context.__class__):
            field = self.field.bind(context)
            context = context.context
        else:
            field = self.field.bind(context)
        file_manager = getMultiAdapter((context, request, field), IFileManager)
        val = await file_manager.save_file(
            self.generator, content_type=self.value['content_type'],
            size=len(self.value['data']))
        return val
