from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.files.dbfile import DBFile
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.json.serialize_value import json_compatible
from guillotina.tests.utils import create_content


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
