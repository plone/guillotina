from datetime import datetime
from guillotina import schema
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.files.dbfile import DBFile
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.json import deserialize_value
from guillotina.json.deserialize_value import schema_compatible
from guillotina.json.serialize_value import json_compatible
from guillotina.tests.utils import create_content
from guillotina.tests.utils import login
from zope.interface import Interface


async def test_serialize_resource(dummy_request):
    content = create_content()
    serializer = get_multi_adapter(
        (content, dummy_request),
        IResourceSerializeToJson)
    result = await serializer()
    assert 'guillotina.behaviors.dublincore.IDublinCore' in result


async def test_serialize_resource_omit_behavior(dummy_request):
    content = create_content()
    serializer = get_multi_adapter(
        (content, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(omit=['guillotina.behaviors.dublincore.IDublinCore'])
    assert 'guillotina.behaviors.dublincore.IDublinCore' not in result


async def test_serialize_resource_omit_field(dummy_request):
    content = create_content()
    serializer = get_multi_adapter(
        (content, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(omit=['guillotina.behaviors.dublincore.IDublinCore.creators'])
    assert 'creators' not in result['guillotina.behaviors.dublincore.IDublinCore']


async def test_serialize_resource_include_field(dummy_request):
    from guillotina.test_package import FileContent
    obj = create_content(FileContent, type_name='File')
    obj.file = DBFile(filename='foobar.json', size=25, md5='foobar')
    serializer = get_multi_adapter(
        (obj, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(include=['guillotina.behaviors.dublincore.IDublinCore.creators'])
    assert 'creators' in result['guillotina.behaviors.dublincore.IDublinCore']
    assert len(result['guillotina.behaviors.dublincore.IDublinCore']) == 1
    assert 'file' not in result


async def test_serialize_omit_main_interface_field(dummy_request):
    from guillotina.test_package import FileContent
    obj = create_content(FileContent, type_name='File')
    obj.file = DBFile(filename='foobar.json', size=25, md5='foobar')
    serializer = get_multi_adapter(
        (obj, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(omit=['file'])
    assert 'file' not in result
    result = await serializer()
    assert 'file' in result


async def test_serialize_cloud_file(dummy_request):
    from guillotina.test_package import FileContent
    obj = create_content(FileContent)
    obj.file = DBFile(filename='foobar.json', size=25, md5='foobar')
    value = json_compatible(obj.file)
    assert value['filename'] == 'foobar.json'
    assert value['size'] == 25
    assert value['md5'] == 'foobar'


async def test_deserialize_cloud_file(dummy_request):
    from guillotina.test_package import IFileContent, FileContent
    request = dummy_request  # noqa
    tm = dummy_request._tm
    await tm.begin(dummy_request)
    obj = create_content(FileContent)
    obj.file = None
    value = await get_adapter(
        IFileContent['file'], IJSONToValue,
        args=[
            'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
            obj
        ])
    assert isinstance(value, DBFile)
    assert value.size == 42


class ITestSchema(Interface):

    text = schema.TextLine()
    integer = schema.Int()
    floating = schema.Float()
    list_of_text = schema.List(value_type=schema.TextLine())
    tuple_of_text = schema.Tuple(value_type=schema.TextLine())
    set_of_text = schema.Set(value_type=schema.TextLine())
    frozenset_of_text = schema.FrozenSet(value_type=schema.TextLine())
    dict_value = schema.Dict(
        key_type=schema.TextLine(),
        value_type=schema.TextLine()
    )
    datetime = schema.Datetime()
    date = schema.Date()
    time = schema.Time()


async def test_deserialize_text(dummy_guillotina):
    assert schema_compatible('foobar', ITestSchema['text']) == 'foobar'


async def test_deserialize_int(dummy_guillotina):
    assert schema_compatible(5, ITestSchema['integer']) == 5


async def test_deserialize_float(dummy_guillotina):
    assert int(schema_compatible(5.5534, ITestSchema['floating'])) == 5


async def test_deserialize_list(dummy_guillotina):
    assert schema_compatible(['foo', 'bar'], ITestSchema['list_of_text']) == ['foo', 'bar']


async def test_deserialize_tuple(dummy_guillotina):
    assert schema_compatible(['foo', 'bar'], ITestSchema['tuple_of_text']) == ('foo', 'bar')


async def test_deserialize_set(dummy_guillotina):
    assert len(schema_compatible(['foo', 'bar'], ITestSchema['set_of_text'])) == 2


async def test_deserialize_frozenset(dummy_guillotina):
    assert len(schema_compatible(['foo', 'bar'], ITestSchema['frozenset_of_text'])) == 2


async def test_deserialize_dict(dummy_guillotina):
    assert schema_compatible({'foo': 'bar'}, ITestSchema['dict_value']) == {'foo': 'bar'}


async def test_deserialize_datetime(dummy_guillotina):
    now = datetime.utcnow()
    converted = schema_compatible(now.isoformat(), ITestSchema['datetime'])
    assert converted.minute == now.minute


async def test_check_permission_deserialize_content(dummy_request):
    request = dummy_request  # noqa
    login(request)
    content = create_content()
    deserializer = get_multi_adapter(
        (content, request), IResourceDeserializeFromJson)
    assert deserializer.check_permission('guillotina.ViewContent')
    assert deserializer.check_permission('guillotina.ViewContent')  # with cache


def test_default_value_deserialize(dummy_request):
    content = create_content()
    assert {'text': 'foobar'} == deserialize_value.default_value_converter(ITestSchema, {
        'text': 'foobar'
    }, content)
