from functools import partial
from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.files.utils import convert_base64_to_binary
from guillotina.files.utils import guess_content_type
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IContentBehavior
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileManager
from guillotina.schema.fieldproperty import FieldProperty
from guillotina.utils import get_current_request
from guillotina.utils import to_str
from zope.interface import implementer

import base64
import uuid


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

    filename: str = FieldProperty(IFile['filename'])  # type: ignore
    valid = True

    def __init__(self, content_type='application/octet-stream',
                 filename=None, size=0, md5=None):
        if isinstance(content_type, bytes):
            content_type = content_type.decode('utf8')
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
        self._current_upload = 0

    def guess_content_type(self):
        return guess_content_type(self.content_type, self.filename)

    @property
    def current_upload(self):
        return self._current_upload

    @current_upload.setter
    def current_upload(self, val):
        self._current_upload = val

    def get_actual_size(self):
        return self._current_upload

    @property
    def uri(self):
        if hasattr(self, '_uri'):
            return self._uri

    @uri.setter
    def uri(self, val):
        self._uri = val

    @property
    def size(self):
        if hasattr(self, '_size'):
            return self._size
        else:
            return None

    @size.setter
    def size(self, val):
        self._size = val

    @property
    def md5(self):
        if hasattr(self, '_md5'):
            return self._md5
        else:
            return None

    @md5.setter
    def md5(self, val):
        self._md5 = val

    @property
    def extension(self):
        if getattr(self, '_extension', None):
            return self._extension
        else:
            if '.' in self.filename:
                return self.filename.split('.')[-1]
            return None

    @extension.setter
    def extension(self, val):
        self._extension = val


async def _generator(value):
    yield value['data']


serialize_mappings = {
    'filename': 'filename',
    'md5': '_md5',
    'content_type': 'content_type',
    'extension': '_extension'
}


@configure.value_deserializer(ICloudFileField)
async def deserialize_cloud_field(field, value, context):
    # It supports base64 web value or a dict
    data_context = context
    if IContentBehavior.implementedBy(context.__class__):
        field = field.bind(context)
        context = context.context
    else:
        field = field.bind(context)

    if isinstance(value, dict):
        try:
            file_ob = field.get(data_context)
        except AttributeError:
            file_ob = None
        if file_ob is not None:
            # update file fields
            for key, item_value in value.items():
                if key in serialize_mappings:
                    setattr(file_ob, serialize_mappings[key], item_value)
            data_context._p_register()
        if 'data' in value:
            value['data'] = base64.b64decode(value['data'])
        else:
            # already updated necessary values
            return file_ob
    else:
        # base64 web value
        value = convert_base64_to_binary(value)

    # There is not file and expecting a dict
    # 'data', 'encoding', 'content-type', 'filename'
    request = get_current_request()
    file_manager = get_multi_adapter((context, request, field), IFileManager)
    content_type = value.get('content_type', value.get('content-type'))
    filename = value.get('filename', None)
    val = await file_manager.save_file(
        partial(_generator, value), content_type=content_type,
        size=len(value['data']), filename=filename)
    return val
