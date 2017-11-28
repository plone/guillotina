from guillotina import schema
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.component import get_utility
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
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.json import deserialize_content
from guillotina.json import serialize_schema
from guillotina.json import serialize_schema_field
from guillotina.json.serialize_content import DefaultJSONSummarySerializer
from guillotina.json.serialize_content import SerializeFolderToJson
from guillotina.json.serialize_content import SerializeToJson
from guillotina.json.serialize_value import json_compatible
from guillotina.security.policy import Interaction


def test_get_current_interaction(dummy_request):
    adapter = get_adapter(dummy_request, interface=IInteraction)
    assert isinstance(adapter, Interaction)


async def test_DatabaseSpecialPermissions_IDatabase(dummy_txn_root):  # noqa: N802
    async with dummy_txn_root as root:
        adapter = get_adapter(root, interface=IPrincipalPermissionManager)
        assert isinstance(adapter, DatabaseSpecialPermissions)


async def test_RootSpecialPermissions_IApplication(dummy_guillotina):  # noqa: N802
    root = get_utility(IApplication, name='root')
    adapter = get_adapter(root, interface=IPrincipalPermissionManager)
    assert isinstance(adapter, ApplicationSpecialPermissions)


async def test_SerializeFolderToJson(dummy_request):  # noqa: N802
    adapter = get_multi_adapter((Container(), dummy_request),
                                interface=IResourceSerializeToJson)
    assert isinstance(adapter, SerializeFolderToJson)


async def test_SerializeToJson(dummy_request):  # noqa: N802
    obj = Item()
    adapter = get_multi_adapter((obj, dummy_request),
                                interface=IResourceSerializeToJson)
    assert isinstance(adapter, SerializeToJson)


def test_DefaultJSONSummarySerializer(dummy_request):  # noqa: N802
    adapter = get_multi_adapter((Container(), dummy_request),
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
        (schema.Date(), serialize_schema_field.DefaultDateSchemaFieldSerializer),
        (schema.Time(), serialize_schema_field.DefaultTimeSchemaFieldSerializer),
        (schema.Dict(), serialize_schema_field.DefaultDictSchemaFieldSerializer),
        (schema.Datetime(), serialize_schema_field.DefaultDateTimeSchemaFieldSerializer),
    ]
    container = Container()
    for field, klass in mapping:
        adapter = get_multi_adapter((field, container, dummy_request),
                                    interface=ISchemaFieldSerializeToJson)
        assert isinstance(adapter, klass)


def test_vocabulary(dummy_request):
    from guillotina.schema.vocabulary import SimpleVocabulary
    vocab = SimpleVocabulary.fromItems((
        (u"Foo", "id_foo"),
        (u"Bar", "id_bar")))
    res = json_compatible(vocab)
    assert type(res) == list


def test_SerializeFactoryToJson(dummy_request):  # noqa: N802
    factory = get_utility(IResourceFactory, name='Item')
    adapter = get_multi_adapter((factory, dummy_request),
                                interface=IFactorySerializeToJson)
    assert isinstance(adapter, serialize_schema.SerializeFactoryToJson)


def test_DefaultSchemaSerializer(dummy_request):  # noqa: N802
    adapter = get_multi_adapter(
        (IItem, dummy_request),
        ISchemaSerializeToJson)
    assert isinstance(adapter, serialize_schema.DefaultSchemaSerializer)


def test_DeserializeFromJson(dummy_request):  # noqa: N802
    obj = Item()
    adapter = get_multi_adapter((obj, dummy_request),
                                interface=IResourceDeserializeFromJson)
    assert isinstance(adapter, deserialize_content.DeserializeFromJson)
