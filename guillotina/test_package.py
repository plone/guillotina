# this is for testing.py, do not import into other modules
from guillotina import configure
from guillotina.content import Item
from guillotina.interfaces import IItem
from guillotina.interfaces import ISite
from guillotina.testing import Example
from guillotina.testing import IExample


configure.register_configuration(Item, dict(
    context=ISite,
    schema=IItem,
    portal_type="File",
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore"
    ]
), 'contenttype')

configure.register_configuration(Example, dict(
    context=ISite,
    schema=IExample,
    portal_type="Example",
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore"
    ]
), 'contenttype')
