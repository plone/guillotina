from functools import partial
from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.files.utils import convert_base64_to_binary
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IContentBehavior
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileManager
from guillotina.schema import Object
from guillotina.schema.fieldproperty import FieldProperty
from guillotina.utils import get_content_path
from guillotina.utils import get_current_request
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


@configure.value_serializer(for_=IFile)
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
        if getattr(self, '_extension', None):
            return self._extension
        else:
            if '.' in self.filename:
                return self.filename.split('.')[-1]
            return None

    async def copy_cloud_file(self, context, new_uri):
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


async def _generator(value):
    yield value['data']


@configure.value_deserializer(ICloudFileField)
async def deserialize_cloud_field(field, value, context):
    request = get_current_request()
    value = convert_base64_to_binary(value)
    if IContentBehavior.implementedBy(context.__class__):
        field = field.bind(context)
        context = context.context
    else:
        field = field.bind(context)
    file_manager = get_multi_adapter((context, request, field), IFileManager)
    val = await file_manager.save_file(
        partial(_generator, value), content_type=value['content_type'],
        size=len(value['data']))
    return val
