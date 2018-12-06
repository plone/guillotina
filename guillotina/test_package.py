# this is for testing.py, do not import into other modules
import json

from guillotina import configure
from guillotina import schema
from guillotina.async_util import IAsyncUtility
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.behaviors.instance import ContextBehavior
from guillotina.content import Item
from guillotina.content import Resource
from guillotina.directives import index_field
from guillotina.directives import metadata
from guillotina.fields import CloudFileField
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IIDGenerator
from guillotina.interfaces import IItem
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IResource
from guillotina.response import HTTPUnprocessableEntity
from zope.interface import Interface
from zope.interface import implementer


app_settings = {
    'applications': ['guillotina']
}


TERM_SCHEMA = json.dumps({
    'type': 'object',
    'properties': {
        'label': {'type': 'string'},
        'number': {'type': 'number'}
    },
})


class IExample(IResource):

    metadata('categories')

    index_field('categories', type='nested')
    categories = schema.List(
        title='categories',
        default=[],
        value_type=schema.JSONField(
            title='term',
            schema=TERM_SCHEMA)
    )

    textline_field = schema.TextLine(
        title='kk', widget='testing', required=False)
    text_field = schema.Text(required=False)
    dict_value = schema.Dict(
        key_type=schema.TextLine(),
        value_type=schema.TextLine(),
        required=False
    )
    datetime = schema.Datetime(required=False)


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


class ITestContextBehavior(Interface):
    foobar = schema.TextLine()


class IMarkerTestContextBehavior(Interface):
    pass


@configure.behavior(
    title="",
    provides=ITestContextBehavior,
    marker=IMarkerTestContextBehavior,
    for_="guillotina.interfaces.IResource")
class GContextTestBehavior(ContextBehavior):
    pass


class ITestNoSerializeBehavior(Interface):
    foobar = schema.TextLine()


@configure.behavior(
    title="",
    provides=ITestNoSerializeBehavior,
    for_="guillotina.interfaces.IResource")
class GTestNoSerializeBehavior(ContextBehavior):
    auto_serialize = False


class IFileContent(IItem):
    file = CloudFileField(required=False)


@configure.contenttype(
    schema=IFileContent, type_name="File",
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore"
    ])
class FileContent(Item):
    pass


@configure.subscriber(
    for_=(IFileContent, IObjectAddedEvent), priority=-1000)
async def foobar_sub(ob, evt):
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


@configure.service(
    context=IApplication, method='GET', permission='guillotina.AccessContent',
    name='@match/{foo}/{bar}')
async def matching_service(context, request):
    return request.matchdict


@configure.adapter(
    for_=Interface,
    provides=IIDGenerator)
class IDGenerator(object):
    """
    Test id generator
    """

    def __init__(self, request):
        self.request = request

    def __call__(self, data):

        if 'bad-id' in data:
            return data['bad-id']

        if 'custom-id' in data:
            return data['custom-id']
