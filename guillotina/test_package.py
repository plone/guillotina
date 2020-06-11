# this is for testing.py, do not import into other modules
from guillotina import configure
from guillotina import fields
from guillotina import schema
from guillotina.async_util import IAsyncUtility
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.behaviors.instance import ContextBehavior
from guillotina.behaviors.properties import ContextProperty
from guillotina.content import Item
from guillotina.content import Resource
from guillotina.directives import index_field
from guillotina.directives import metadata
from guillotina.directives import read_permission
from guillotina.directives import write_permission
from guillotina.exceptions import NoIndexField
from guillotina.fields import CloudFileField
from guillotina.files import BaseCloudFile
from guillotina.files.exceptions import RangeNotFound
from guillotina.files.utils import generate_key
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IExternalFileStorageManager
from guillotina.interfaces import IFile
from guillotina.interfaces import IFileField
from guillotina.interfaces import IIDGenerator
from guillotina.interfaces import IItem
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.response import HTTPUnprocessableEntity
from guillotina.schema import Object
from guillotina.schema.interfaces import IContextAwareDefaultFactory
from shutil import copyfile
from typing import AsyncIterator
from zope.interface import implementer
from zope.interface import Interface

import json
import os
import tempfile
import typing


app_settings = {"applications": ["guillotina"]}


TERM_SCHEMA = json.dumps(
    {"type": "object", "properties": {"label": {"type": "string"}, "number": {"type": "number"}}}
)


@implementer(IContextAwareDefaultFactory)
class ContextDefaultFactory:
    def __call__(self, context):
        return "foobar"


CATEGORIES_MAPPING = {"dynamic": False, "type": "nested"}


class IExample(IResource):

    metadata("categories")

    index_field("boolean_field", type="boolean")
    boolean_field = schema.Bool(required=False)

    index_field("categories", field_mapping=CATEGORIES_MAPPING)
    categories = schema.List(
        title="categories", default=[], value_type=schema.JSONField(title="term", schema=TERM_SCHEMA)
    )

    textline_field = schema.TextLine(title="kk", widget="testing", required=False)
    text_field = schema.Text(required=False)
    dict_value = schema.Dict(key_type=schema.TextLine(), value_type=schema.TextLine(), required=False)
    datetime = schema.Datetime(required=False)

    write_permission(write_protected="example.MyPermission")
    write_protected = schema.TextLine(title="Write protected field", required=False)

    default_factory_test = schema.Text(defaultFactory=lambda: "foobar")

    context_default_factory_test = schema.Text(defaultFactory=ContextDefaultFactory())


@index_field.with_accessor(IExample, "categories_accessor", field="categories")
def categories_index_accessor(ob):
    if not ob.categories:
        raise NoIndexField
    else:
        return [c["label"] for c in ob.categories]


@index_field.with_accessor(IExample, "foobar_accessor")
def foobar_accessor(ob):
    return "foobar"


configure.permission("example.MyPermission", "example permission")


@implementer(IExample)
class Example(Resource):  # type: ignore
    pass


class IMarkerBehavior(Interface):
    pass


class ITestBehavior(Interface):
    foobar = schema.TextLine(required=False)
    foobar_context = schema.TextLine(required=False, default="default-foobar")

    bucket_dict = fields.BucketDictField(
        bucket_len=10, required=False, default=None, key_type=schema.Text(), value_type=schema.Text()
    )

    bucket_list = fields.BucketListField(
        bucket_len=10, required=False, default=None, value_type=schema.Text()
    )

    read_permission(no_read_field="example.MyPermission")
    no_read_field = schema.TextLine(required=False, default="")

    test_required_field = schema.TextLine(required=True)


@configure.behavior(
    title="", provides=ITestBehavior, marker=IMarkerBehavior, for_="guillotina.interfaces.IResource"
)
class GTestBehavior(AnnotationBehavior):
    foobar_context = ContextProperty("foobar_context")


class ITestContextBehavior(Interface):
    foobar = schema.TextLine()


class IMarkerTestContextBehavior(Interface):
    pass


@configure.behavior(
    title="",
    provides=ITestContextBehavior,
    marker=IMarkerTestContextBehavior,
    for_="guillotina.interfaces.IResource",
)
class GContextTestBehavior(ContextBehavior):
    pass


class ITestNoSerializeBehavior(Interface):
    foobar = schema.TextLine()


@configure.behavior(title="", provides=ITestNoSerializeBehavior, for_="guillotina.interfaces.IResource")
class GTestNoSerializeBehavior(ContextBehavior):
    auto_serialize = False


class IFileContent(IItem):
    file = CloudFileField(required=False)


@configure.contenttype(
    schema=IFileContent, type_name="File", behaviors=["guillotina.behaviors.dublincore.IDublinCore"]
)
class FileContent(Item):
    pass


@configure.subscriber(for_=(IFileContent, IObjectAddedEvent), priority=-1000)
async def foobar_sub(ob, evt):
    pass


@configure.subscriber(for_=(IResource, IObjectAddedEvent), priority=-1000)
def sync_foobar_sub(ob, evt):
    if not hasattr(evt, "called"):
        evt.called = 0
    evt.called += 1


configure.register_configuration(
    Example,
    dict(
        context=IContainer,
        schema=IExample,
        type_name="Example",
        behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
    ),
    "contenttype",
)


@configure.service(
    context=IApplication, method="GET", permission="guillotina.AccessContent", name="@raise-http-exception"
)
@configure.service(
    context=IApplication, method="POST", permission="guillotina.AccessContent", name="@raise-http-exception"
)
async def raise_http_exception(context, request):
    raise HTTPUnprocessableEntity()


# Create a new permission and grant it to authenticated users only
configure.permission("example.EndpointPermission", "example permission")
configure.grant(permission="example.EndpointPermission", role="guillotina.Authenticated")


@configure.service(
    context=IApplication, method="GET", permission="example.EndpointPermission", name="@myEndpoint"
)
async def my_endpoint(context, request):
    return {"foo": "bar"}


@configure.service(
    context=IApplication,
    method="GET",
    permission="guillotina.AccessContent",
    name="@json-schema-validation",
    validate=True,
    parameters=[
        {"name": "foo", "in": "query", "schema": {"type": "number"}, "required": True},
        {"name": "bar", "in": "query", "schema": {"type": "string"}, "required": False},
    ],
)
async def json_schema_query_validation(context, request):
    return {}


class ITestAsyncUtility(IAsyncUtility):
    pass


@configure.utility(provides=ITestAsyncUtility)
class AsyncUtility:
    def __init__(self, settings=None, loop=None):
        self.state = "init"

    async def initialize(self):
        self.state = "initialize"

    async def finalize(self):
        self.state = "finalize"


@configure.service(
    context=IApplication, method="GET", permission="guillotina.AccessContent", name="@match/{foo}/{bar}"
)
async def matching_service(context, request):
    return request.matchdict


@configure.service(
    context=IApplication,
    method="GET",
    permission="guillotina.Public",
    name="@queryParamsValidation",
    parameters=[
        {
            "required": False,
            "in": "query",
            "name": "users",
            "schema": {
                "minItems": 2,
                "maxItems": 5,
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
        },
        {
            "required": False,
            "in": "query",
            "name": "numbers",
            "schema": {"type": "array", "items": {"type": "number"}},
        },
        {
            "required": False,
            "in": "query",
            "name": "oranges",
            "schema": {"type": "integer", "minimum": 2, "maximum": 10},
        },
        {
            "required": False,
            "in": "query",
            "name": "kilograms",
            "schema": {"type": "number", "minimum": 50, "maximum": 100},
        },
    ],
    validate=True,
)
async def dummy_query_params_service(context, request):
    return {}


@configure.service(
    context=IApplication,
    method="POST",
    name="@optionalRequestBody",
    requestBody={
        "required": False,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["valid"],
                    "properties": {"valid": {"type": "string"}},
                }
            }
        },
    },
    validate=True,
)
async def dummy_request_body_validator(context, request):
    return {}


@configure.adapter(for_=Interface, provides=IIDGenerator)
class IDGenerator(object):
    """
    Test id generator
    """

    def __init__(self, request):
        self.request = request

    def __call__(self, data):

        if "bad-id" in data:
            return data["bad-id"]

        if "custom-id" in data:
            return data["custom-id"]


class IMemoryFileField(IFileField):
    """
    """


class IInMemoryCloudFile(IFile):
    """
    """


@configure.adapter(for_=(dict, IMemoryFileField), provides=IJSONToValue)
def dictfile_converter(value, field):
    return MemoryFile(**value)


@implementer(IInMemoryCloudFile)
class MemoryFile(BaseCloudFile):  # type: ignore
    """File stored in a GCloud, with a filename."""

    _chunks = 0
    _size = 0

    @property
    def chunks(self):
        return self._chunks

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, val):
        self._size = val


_tmp_files: typing.Dict = {}


@configure.adapter(for_=(IResource, IRequest, IMemoryFileField), provides=IExternalFileStorageManager)
class InMemoryFileManager:

    file_class = MemoryFile

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

    async def iter_data(self, uri=None):
        if uri is None:
            file = self.field.get(self.field.context or self.context)
            uri = file.uri
        with open(_tmp_files[uri], "rb") as fi:
            chunk = fi.read(1024)
            while chunk:
                yield chunk
                chunk = fi.read(1024)

    async def start(self, dm):
        upload_file_id = dm.get("upload_file_id")
        if upload_file_id is not None:
            await self.delete_upload(upload_file_id)

        upload_file_id = generate_key(self.context)
        _tmp_files[upload_file_id] = tempfile.mkstemp()[1]
        await dm.update(_chunks=0, upload_file_id=upload_file_id)

    async def delete_upload(self, uri):  # pragma: no cover
        if uri in _tmp_files:
            if os.path.exists(_tmp_files[uri]):
                os.remove(_tmp_files[uri])
            del _tmp_files[uri]

    async def range_supported(self) -> bool:
        return True

    async def read_range(self, start: int, end: int) -> AsyncIterator[bytes]:
        file = self.field.get(self.field.context or self.context)
        uri = file.uri
        total = 0
        with open(_tmp_files[uri], "rb") as fi:
            fi.seek(start)
            while total < (end - start):
                chunk = fi.read(1024 * 1024)
                total += len(chunk)
                yield chunk
        if len(chunk) != (end - start):
            raise RangeNotFound(field=self.field, start=start, end=end)

    async def append(self, dm, iterable, offset) -> int:
        count = 0
        file_id = dm.get("upload_file_id")
        chunk_count = dm.get("_chunks")
        with open(_tmp_files[file_id], "ab") as fi:
            async for chunk in iterable:
                if chunk:
                    fi.write(chunk)
                    count += len(chunk)
                    chunk_count += 1
        await dm.update(_chunks=chunk_count)
        return count

    async def finish(self, dm):
        await dm.update(uri=dm.get("upload_file_id"), upload_file_id=None)

    async def exists(self):
        file = self.field.get(self.field.context or self.context)
        return file.uri in _tmp_files and os.path.exists(_tmp_files[file.uri])

    async def copy(self, to_storage_manager, to_dm):
        file = self.field.get(self.field.context or self.context)
        new_uri = generate_key(self.context)
        _tmp_files[new_uri] = _tmp_files[file.uri]
        _tmp_files[new_uri] = tempfile.mkstemp()[1]
        copyfile(_tmp_files[file.uri], _tmp_files[new_uri])
        await to_dm.finish(
            values={
                "content_type": file.content_type,
                "size": file.size,
                "uri": new_uri,
                "filename": file.filename or "unknown",
            }
        )


@implementer(IMemoryFileField)
class InMemoryFileField(Object):
    """A NamedBlobFile field."""

    _type = MemoryFile
    schema = IInMemoryCloudFile

    def __init__(self, **kw):
        if "schema" in kw:
            self.schema = kw.pop("schema")
        super(InMemoryFileField, self).__init__(schema=self.schema, **kw)
