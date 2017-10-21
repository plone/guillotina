# this is for testing.py, do not import into other modules
from guillotina import configure
from guillotina.content import Item
from guillotina.files import CloudFileField
from guillotina.interfaces import IContainer
from guillotina.interfaces import IItem
from guillotina.testing import Example
from guillotina.testing import IExample


class IFileContent(IItem):
    file = CloudFileField(required=False)


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
