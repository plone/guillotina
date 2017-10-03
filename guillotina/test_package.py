# this is for testing.py, do not import into other modules
from guillotina import configure
from guillotina.content import Item
from guillotina.files import BaseCloudFile
from guillotina.files import CloudFileField
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IContainer
from guillotina.interfaces import IFile
from guillotina.interfaces import IItem
from guillotina.interfaces import IJSONToValue
from guillotina.testing import Example
from guillotina.testing import IExample
from zope.interface import implementer


class IFileContent(IItem):
    file = CloudFileField(required=False)


@implementer(IFile)
class CloudFile(BaseCloudFile):

    _size = 0
    _md5 = None
    _data = b''

    def __init__(self, content_type='application/octet-stream',
                 filename=None, size=0, md5=None, data=b''):
        super().__init__(
            content_type=content_type, filename=filename, size=size, md5=md5)
        self._data = data

    @property
    def data(self):
        return self._data


@configure.adapter(
    for_=(dict, ICloudFileField),
    provides=IJSONToValue)
def dictfile_converter(value, field):
    return CloudFile(**value)


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
