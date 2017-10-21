from guillotina.component import getMultiAdapter
from guillotina.component import queryMultiAdapter
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.interfaces import IResourceFieldSerializer
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.tests.utils import create_content


async def test_serialize_resource(dummy_request):
    content = create_content()
    serializer = getMultiAdapter(
        (content, dummy_request),
        IResourceSerializeToJson)
    result = await serializer()
    assert 'guillotina.behaviors.dublincore.IDublinCore' in result


async def test_serialize_resource_omit_behavior(dummy_request):
    content = create_content()
    serializer = getMultiAdapter(
        (content, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(omit=['guillotina.behaviors.dublincore.IDublinCore'])
    assert 'guillotina.behaviors.dublincore.IDublinCore' not in result


async def test_serialize_resource_omit_field(dummy_request):
    content = create_content()
    serializer = getMultiAdapter(
        (content, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(omit=['guillotina.behaviors.dublincore.IDublinCore.creators'])
    assert 'creators' not in result['guillotina.behaviors.dublincore.IDublinCore']


async def test_serialize_resource_include_field(dummy_request):
    from guillotina.test_package import FileContent, CloudFile
    obj = create_content(FileContent, type_name='File')
    obj.file = CloudFile(filename='foobar.json', size=25, md5='foobar')
    serializer = getMultiAdapter(
        (obj, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(include=['guillotina.behaviors.dublincore.IDublinCore.creators'])
    assert 'creators' in result['guillotina.behaviors.dublincore.IDublinCore']
    assert len(result['guillotina.behaviors.dublincore.IDublinCore']) == 1
    assert 'file' not in result


async def test_serialize_omit_main_interface_field(dummy_request):
    from guillotina.test_package import FileContent, CloudFile
    obj = create_content(FileContent, type_name='File')
    obj.file = CloudFile(filename='foobar.json', size=25, md5='foobar')
    serializer = getMultiAdapter(
        (obj, dummy_request),
        IResourceSerializeToJson)
    result = await serializer(omit=['file'])
    assert 'file' not in result
    result = await serializer()
    assert 'file' in result


async def test_serialize_cloud_file(dummy_request):
    from guillotina.test_package import IFileContent, FileContent, CloudFile
    obj = create_content(FileContent)
    obj.file = CloudFile(filename='foobar.json', size=25, md5='foobar')
    serializer = queryMultiAdapter(
        (IFileContent['file'], obj, dummy_request),
        IResourceFieldSerializer)
    value = await serializer()
    assert value['filename'] == 'foobar.json'
    assert value['size'] == 25
    assert value['md5'] == 'foobar'


async def test_deserialize_cloud_file(dummy_request):
    from guillotina.test_package import IFileContent, FileContent, CloudFile
    obj = FileContent()
    deserializer = queryMultiAdapter(
        (IFileContent['file'], obj, dummy_request),
        IResourceFieldDeserializer)
    value = await deserializer({
        'filename': 'foobar.json',
        'size': 25,
        'md5': 'foobar'
    })

    assert isinstance(value, CloudFile)
    assert value.size == 25
    assert value.filename == 'foobar.json'
    assert value.md5 == 'foobar'
