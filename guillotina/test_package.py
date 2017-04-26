# this is for testing.py, do not import into other modules
from guillotina import configure
from guillotina.content import Item
from guillotina.files import CloudFileField
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IContainer
from guillotina.interfaces import IFile
from guillotina.interfaces import IItem
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IValueToJson
from guillotina.schema.fieldproperty import FieldProperty
from guillotina.testing import Example
from guillotina.testing import IExample
from zope.interface import implementer

import uuid


class IFileContent(IItem):
    file = CloudFileField(required=False)


@implementer(IFile)
class CloudFile:

    filename = FieldProperty(IFile['filename'])
    _size = 0
    _md5 = None
    _data = b''

    def __init__(self, content_type='application/octet-stream',
                 filename=None, size=0, md5=None, data=b''):
        if not isinstance(content_type, bytes):
            content_type = content_type.encode('utf8')
        self.content_type = content_type
        if filename is not None:
            self.filename = filename
            extension_discovery = filename.split('.')
            if len(extension_discovery) > 1:
                self._extension = extension_discovery[-1]
        elif self.filename is not None:
            self.filename = uuid.uuid4().hex

        self._size = size
        self._md5 = md5
        self._data = data

    @property
    def data(self):
        return self._data

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


@configure.adapter(
    for_=(dict, ICloudFileField),
    provides=IJSONToValue)
def dictfile_converter(value, field):
    return CloudFile(**value)


@configure.adapter(for_=IFile, provides=IValueToJson)
def json_converter(value):
    if value is None:
        return value

    return {
        'filename': value.filename,
        'contenttype': value.content_type,
        'size': value.size,
        'extension': value.extension,
        'md5': value.md5
    }


@configure.contenttype(
    schema=IFileContent, type_name="File",
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore"
    ])
class FileContent(Item):
    pass


configure.register_configuration(Example, dict(
    context=IContainer,
    schema=IExample,
    type_name="Example",
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore"
    ]
), 'contenttype')
