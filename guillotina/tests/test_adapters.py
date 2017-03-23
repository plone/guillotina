# -*- coding: utf-8 -*-
from guillotina import schema
from guillotina.component import getAdapter
from guillotina.component import getMultiAdapter
from guillotina.component import getUtility
from guillotina.content import Container
from guillotina.content import Item
from guillotina.factory.security import ApplicationSpecialPermissions
from guillotina.factory.security import DatabaseSpecialPermissions
from guillotina.interfaces import IApplication
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IItem
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceFactory
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.interfaces import IResourceFieldSerializer
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.interfaces import IValueToJson
from guillotina.json import deserialize_content
from guillotina.json import deserialize_content_fields
from guillotina.json import serialize_content_field
from guillotina.json import serialize_schema
from guillotina.json import serialize_schema_field
from guillotina.json.serialize_content import DefaultJSONSummarySerializer
from guillotina.json.serialize_content import SerializeFolderToJson
from guillotina.json.serialize_content import SerializeToJson
from guillotina.security.policy import Interaction
from guillotina.text import RichText


def test_get_current_interaction(dummy_request):
    adapter = getAdapter(dummy_request, interface=IInteraction)
    assert isinstance(adapter, Interaction)


async def test_DatabaseSpecialPermissions_IDatabase(dummy_txn_root):
    async with await dummy_txn_root as root:
        adapter = getAdapter(root, interface=IPrincipalPermissionManager)
        assert isinstance(adapter, DatabaseSpecialPermissions)


async def test_RootSpecialPermissions_IApplication(dummy_guillotina):
    root = getUtility(IApplication, name='root')
    adapter = getAdapter(root, interface=IPrincipalPermissionManager)
    assert isinstance(adapter, ApplicationSpecialPermissions)


async def test_SerializeFolderToJson(dummy_request):
    adapter = getMultiAdapter((Container(), dummy_request),
                              interface=IResourceSerializeToJson)
    assert isinstance(adapter, SerializeFolderToJson)


async def test_SerializeToJson(dummy_request):
    obj = Item()
    adapter = getMultiAdapter((obj, dummy_request),
                              interface=IResourceSerializeToJson)
    assert isinstance(adapter, SerializeToJson)


def test_DefaultJSONSummarySerializer(dummy_request):
    adapter = getMultiAdapter((Container(), dummy_request),
                              interface=IResourceSerializeToJsonSummary)
    assert isinstance(adapter, DefaultJSONSummarySerializer)


def test_all(dummy_request):
    mapping = [
        (schema.Object(schema=IResource), serialize_schema_field.DefaultSchemaFieldSerializer),
        (schema.Text(), serialize_schema_field.DefaultTextSchemaFieldSerializer),
        (schema.TextLine(), serialize_schema_field.DefaultTextLineSchemaFieldSerializer),
        (schema.Float(), serialize_schema_field.DefaultFloatSchemaFieldSerializer),
        (schema.Int(), serialize_schema_field.DefaultIntSchemaFieldSerializer),
        (schema.Bool(), serialize_schema_field.DefaultBoolSchemaFieldSerializer),
        (schema.List(), serialize_schema_field.DefaultCollectionSchemaFieldSerializer),
        (schema.Choice(values=('one', 'two')),
            serialize_schema_field.DefaultChoiceSchemaFieldSerializer),
        (schema.Object(schema=IResource),
            serialize_schema_field.DefaultObjectSchemaFieldSerializer),
        (RichText(), serialize_schema_field.DefaultRichTextSchemaFieldSerializer),
        (schema.Date(), serialize_schema_field.DefaultDateSchemaFieldSerializer),
        (schema.Time(), serialize_schema_field.DefaultTimeSchemaFieldSerializer),
        (schema.Dict(), serialize_schema_field.DefaultDictSchemaFieldSerializer),
        (schema.Datetime(), serialize_schema_field.DefaultDateTimeSchemaFieldSerializer),
    ]
    container = Container()
    for field, klass in mapping:
        adapter = getMultiAdapter((field, container, dummy_request),
                                  interface=ISchemaFieldSerializeToJson)
        assert isinstance(adapter, klass)


def test_vocabulary():
    from guillotina.schema.vocabulary import SimpleVocabulary
    vocab = SimpleVocabulary.fromItems((
        (u"Foo", "id_foo"),
        (u"Bar", "id_bar")))
    res = getAdapter(vocab, interface=IValueToJson)
    assert type(res) == list


def test_SerializeFactoryToJson(dummy_request):
    factory = getUtility(IResourceFactory, name='Item')
    adapter = getMultiAdapter((factory, dummy_request),
                              interface=IFactorySerializeToJson)
    assert isinstance(adapter, serialize_schema.SerializeFactoryToJson)


def test_DefaultSchemaSerializer(dummy_request):
    adapter = getMultiAdapter(
        (IItem, dummy_request),
        ISchemaSerializeToJson)
    assert isinstance(adapter, serialize_schema.DefaultSchemaSerializer)


def test_DefaultFieldSerializer(dummy_request):
    obj = Item()
    adapter = getMultiAdapter((schema.Text(), obj, dummy_request),
                              interface=IResourceFieldSerializer)
    assert isinstance(adapter, serialize_content_field.DefaultFieldSerializer)


def test_DeserializeFromJson(dummy_request):
    obj = Item()
    adapter = getMultiAdapter((obj, dummy_request),
                              interface=IResourceDeserializeFromJson)
    assert isinstance(adapter, deserialize_content.DeserializeFromJson)


def test_DefaultResourceFieldDeserializer(dummy_request):
    obj = Item()
    adapter = getMultiAdapter((schema.Text(), obj, dummy_request),
                              interface=IResourceFieldDeserializer)
    assert isinstance(adapter, deserialize_content_fields.DefaultResourceFieldDeserializer)
