from guillotina.component import queryMultiAdapter
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.interfaces import IResourceFieldSerializer


async def test_serialize_cloud_file(dummy_request):
    from guillotina.test_package import IFileContent, FileContent, CloudFile
    obj = FileContent()
    obj.file = CloudFile(filename='foobar.json', size=25, md5='foobar')
    # deserializer = queryMultiAdapter(
    #     (IFile['file'], obj, dummy_request),
    #     IResourceFieldDeserializer)
    # value = deserializer(data_value)
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
    value = deserializer({
        'filename': 'foobar.json',
        'size': 25,
        'md5': 'foobar'
    })

    assert isinstance(value, CloudFile)
    assert value.size == 25
    assert value.filename == 'foobar.json'
    assert value.md5 == 'foobar'
