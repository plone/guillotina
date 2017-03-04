# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import time
from guillotina.content import create_content_in_container
from guillotina.factory import RootSpecialPermissions
from guillotina.files import BasicFile
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
from guillotina.testing import GuillotinaFunctionalTestCase
from guillotina.text import RichText
from persistent.list import PersistentList
from persistent.mapping import PersistentMapping
from zope import schema
from zope.component import getAdapter
from zope.component import getMultiAdapter
from zope.component import getUtility

import pytest


class TestAdapters(GuillotinaFunctionalTestCase):
    """
    mostly to test adapter registrations
    """

    def test_get_current_interaction(self):
        adapter = getAdapter(self.request, interface=IInteraction)
        self.assertTrue(isinstance(adapter, Interaction))

    def test_RootSpecialPermissions_IDatabase(self):
        root = self.new_root()
        adapter = getAdapter(root, interface=IPrincipalPermissionManager)
        self.assertTrue(isinstance(adapter, RootSpecialPermissions))

    def test_RootSpecialPermissions_IApplication(self):
        adapter = getAdapter(self.layer.app, interface=IPrincipalPermissionManager)
        self.assertTrue(isinstance(adapter, RootSpecialPermissions))


class TestSerializerContentAdapters(GuillotinaFunctionalTestCase):
    def test_SerializeFolderToJson(self):
        root = self.new_root()
        site = root['guillotina']
        adapter = getMultiAdapter((site, self.request),
                                  interface=IResourceSerializeToJson)
        self.assertTrue(isinstance(adapter, SerializeFolderToJson))

    @pytest.mark.asyncio
    async def test_SerializeToJson(self):
        root = self.new_root()
        site = root['guillotina']
        self.login()
        obj = await create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((obj, self.request),
                                  interface=IResourceSerializeToJson)
        self.assertTrue(isinstance(adapter, SerializeToJson))
        self.assertFalse(isinstance(adapter, SerializeFolderToJson))

    def test_DefaultJSONSummarySerializer(self):
        root = self.new_root()
        site = root['guillotina']
        adapter = getMultiAdapter((site, self.request),
                                  interface=IResourceSerializeToJsonSummary)
        self.assertTrue(isinstance(adapter, DefaultJSONSummarySerializer))


class TestSerializerFieldAdapters(GuillotinaFunctionalTestCase):
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
        root = self.new_root()
        site = root['guillotina']
        for field, klass in mapping:
            adapter = getMultiAdapter((field, site, self.request),
                                      interface=ISchemaFieldSerializeToJson)
            self.assertTrue(
                isinstance(adapter, klass))


class TestSerializerValueAdapters(GuillotinaFunctionalTestCase):
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


class TestSerializerSchemaAdapters(GuillotinaFunctionalTestCase):
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

    @pytest.mark.asyncio
    async def test_DefaultFieldSerializer(self):
        root = self.new_root()
        site = root['guillotina']
        self.login()
        obj = await create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((schema.Text(), obj, self.request),
                                  interface=IResourceFieldSerializer)
        self.assertTrue(
            isinstance(adapter, serialize_content_field.DefaultFieldSerializer))


class TestDerializeAdapters(GuillotinaFunctionalTestCase):

    @pytest.mark.asyncio
    async def test_DeserializeFromJson(self):
        root = self.new_root()
        site = root['guillotina']
        self.login()
        obj = await create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((obj, self.request),
                                  interface=IResourceDeserializeFromJson)
        self.assertTrue(
            isinstance(adapter, deserialize_content.DeserializeFromJson))

    @pytest.mark.asyncio
    async def test_DefaultResourceFieldDeserializer(self):
        root = self.new_root()
        site = root['guillotina']
        self.login()
        obj = await create_content_in_container(site, 'Item', 'foobar')
        adapter = getMultiAdapter((schema.Text(), obj, self.request),
                                  interface=IResourceFieldDeserializer)
        self.assertTrue(
            isinstance(adapter, deserialize_content_fields.DefaultResourceFieldDeserializer))
