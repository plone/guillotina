# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import time
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from plone.server.content import create_content_in_container
from plone.server.factory import RootSpecialPermissions
from plone.server.file import BasicFile
from plone.server.interfaces import IFactorySerializeToJson
from plone.server.interfaces import IItem
from plone.server.interfaces import IResource
from plone.server.interfaces import IResourceFactory
from plone.server.interfaces import IResourceFieldSerializer
from plone.server.interfaces import IResourceSerializeToJson
from plone.server.interfaces import IResourceSerializeToJsonSummary
from plone.server.interfaces import ISchemaFieldSerializeToJson
from plone.server.interfaces import ISchemaSerializeToJson, IResourceFieldDeserializer
from plone.server.interfaces import IValueToJson, IResourceDeserializeFromJson
from plone.server.json import serialize_content_field
from plone.server.json import serialize_schema
from plone.server.json import serialize_schema_field, deserialize_content, deserialize_content_fields, deserialize_value
from plone.server.json.serialize_content import DefaultJSONSummarySerializer
from plone.server.json.serialize_content import SerializeFolderToJson
from plone.server.json.serialize_content import SerializeToJson
from plone.server.auth.policy import Interaction
from plone.server.testing import PloneFunctionalTestCase
from plone.server.text import RichText
from zope import schema
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.security.interfaces import IInteraction
from plone.server.interfaces import IPrincipalPermissionManager


class TestAdapters(PloneFunctionalTestCase):
    """
    mostly to test adapter registrations
    """

    def test_get_current_interaction(self):
        adapter = getAdapter(self.request, interface=IInteraction)
        self.assertTrue(isinstance(adapter, Interaction))

    def test_RootSpecialPermissions_IDatabase(self):
        root = self.layer.new_root()
        adapter = getAdapter(root, interface=IPrincipalPermissionManager)
        self.assertTrue(isinstance(adapter, RootSpecialPermissions))

    def test_RootSpecialPermissions_IApplication(self):
        adapter = getAdapter(self.layer.app, interface=IPrincipalPermissionManager)
        self.assertTrue(isinstance(adapter, RootSpecialPermissions))


class TestSerializerContentAdapters(PloneFunctionalTestCase):
    def test_SerializeFolderToJson(self):
        root = self.layer.new_root()
        site = root['plone']
        adapter = getMultiAdapter((site, self.request),
                                  interface=IResourceSerializeToJson)
        self.assertTrue(isinstance(adapter, SerializeFolderToJson))

    def test_SerializeToJson(self):
        root = self.layer.new_root()
        site = root['plone']
        self.login()
        obj = create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((obj, self.request),
                                  interface=IResourceSerializeToJson)
        self.assertTrue(isinstance(adapter, SerializeToJson))
        self.assertFalse(isinstance(adapter, SerializeFolderToJson))

    def test_DefaultJSONSummarySerializer(self):
        root = self.layer.new_root()
        site = root['plone']
        adapter = getMultiAdapter((site, self.request),
                                  interface=IResourceSerializeToJsonSummary)
        self.assertTrue(isinstance(adapter, DefaultJSONSummarySerializer))


class TestSerializerFieldAdapters(PloneFunctionalTestCase):
    def test_all(self):
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
        root = self.layer.new_root()
        site = root['plone']
        for field, klass in mapping:
            adapter = getMultiAdapter((field, site, self.request),
                                      interface=ISchemaFieldSerializeToJson)
            self.assertTrue(
                isinstance(adapter, klass))


class TestSerializerValueAdapters(PloneFunctionalTestCase):
    def test_basic_file(self):
        fi = BasicFile()
        res = getAdapter(fi, interface=IValueToJson)
        self.assertTrue('filename' in res)

    def test_vocabulary(self):
        from zope.schema.vocabulary import SimpleVocabulary
        vocab = SimpleVocabulary.fromItems((
            (u"Foo", "id_foo"),
            (u"Bar", "id_bar")))
        res = getAdapter(vocab, interface=IValueToJson)
        self.assertEqual(type(res), list)

    def test_simple(self):
        values = [
            'foobar',
            ['foobar'],
            PersistentList(['foobar']),
            ('foobar',),
            frozenset(['foobar']),
            set(['foobar']),
            {'foo': 'bar'},
            PersistentMapping({'foo': 'bar'}),
            datetime.utcnow(),
            date.today(),
            time()
        ]
        for value in values:
            getAdapter(value, interface=IValueToJson)


class TestSerializerSchemaAdapters(PloneFunctionalTestCase):
    def test_SerializeFactoryToJson(self):
        factory = getUtility(IResourceFactory, name='Item')
        adapter = getMultiAdapter((factory, self.request),
                                  interface=IFactorySerializeToJson)
        self.assertTrue(
            isinstance(adapter, serialize_schema.SerializeFactoryToJson))

    def test_DefaultSchemaSerializer(self):
        adapter = getMultiAdapter(
            (IItem, self.request),
            ISchemaSerializeToJson)
        self.assertTrue(
            isinstance(adapter, serialize_schema.DefaultSchemaSerializer))

    def test_DefaultFieldSerializer(self):
        root = self.layer.new_root()
        site = root['plone']
        self.login()
        obj = create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((schema.Text(), obj, self.request),
                                  interface=IResourceFieldSerializer)
        self.assertTrue(
            isinstance(adapter, serialize_content_field.DefaultFieldSerializer))


class TestDerializeAdapters(PloneFunctionalTestCase):
    def test_DeserializeFromJson(self):
        root = self.layer.new_root()
        site = root['plone']
        self.login()
        obj = create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((obj, self.request),
                                  interface=IResourceDeserializeFromJson)
        self.assertTrue(
            isinstance(adapter, deserialize_content.DeserializeFromJson))

    def test_DefaultResourceFieldDeserializer(self):
        root = self.layer.new_root()
        site = root['plone']
        self.login()
        obj = create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((schema.Text(), obj, self.request),
                                  interface=IResourceFieldDeserializer)
        self.assertTrue(
            isinstance(adapter, deserialize_content_fields.DefaultResourceFieldDeserializer))
