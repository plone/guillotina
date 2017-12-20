# this is for testing.py, do not import into other modules
from aiohttp.web_exceptions import HTTPUnprocessableEntity
from guillotina import configure
from guillotina import schema
from guillotina.async import IAsyncUtility
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.content import Item
from guillotina.content import Resource
from guillotina.directives import index
from guillotina.directives import metadata
from guillotina.files import CloudFileField
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IItem
from guillotina.interfaces import IResource
from zope.interface import implementer
from zope.interface import Interface

import json


TERM_SCHEMA = json.dumps({
    'type': 'object',
    'properties': {
        'label': {'type': 'string'},
        'number': {'type': 'number'}
    },
})


class IExample(IResource):

    metadata('categories')

    index('categories', type='nested')
    categories = schema.List(
        title='categories',
        default=[],
        value_type=schema.JSONField(
            title='term',
            schema=TERM_SCHEMA)
    )

    textline_field = schema.TextLine()
    text_field = schema.Text()
    dict_value = schema.Dict(
        key_type=schema.TextLine(),
        value_type=schema.TextLine()
    )
    datetime = schema.Datetime()


@implementer(IExample)
class Example(Resource):
    pass


class IMarkerBehavior(Interface):
    pass


class ITestBehavior(Interface):
    foobar = schema.TextLine()


@configure.behavior(
    title="",
    provides=ITestBehavior,
    marker=IMarkerBehavior,
    for_="guillotina.interfaces.IResource")
class GTestBehavior(AnnotationBehavior):
    pass


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


@configure.service(
    context=IApplication, method='GET', permission='guillotina.AccessContent',
    name='@raise-http-exception')
@configure.service(
    context=IApplication, method='POST', permission='guillotina.AccessContent',
    name='@raise-http-exception')
async def raise_http_exception(context, request):
    raise HTTPUnprocessableEntity()


class ITestAsyncUtility(IAsyncUtility):
    pass


@configure.utility(provides=ITestAsyncUtility)
class AsyncUtility:
    def __init__(self, settings=None, loop=None):
        self.state = 'init'

    async def initialize(self):
        self.state = 'initialize'

    async def finalize(self):
        self.state = 'finalize'
