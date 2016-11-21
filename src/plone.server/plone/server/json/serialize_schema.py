# -*- coding: utf-8 -*-
from plone.server.interfaces import IRequest
from plone.server.json.interfaces import IFactorySerializeToJson
from plone.server.json.interfaces import ISchemaFieldSerializeToJson
from plone.server.json.interfaces import ISchemaSerializeToJson
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component.interfaces import IFactory
from zope.interface import implementer
from zope.interface import Interface
from zope.schema import getFieldsInOrder


@implementer(IFactorySerializeToJson)
@adapter(IFactory, IRequest)
class SerializeFactoryToJson(object):

    def __init__(self, factory, request):
        self.factory = factory
        self.request = request

    def __call__(self):
        factory = self.factory
        result = {
            'title': factory.portal_type,
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'object',
            'required': [],
            'definitions': {},
            'properties': {
            },
        }

        # Base object class serialized
        for name, field in getFieldsInOrder(factory.schema):
            if field.required:
                result['required'].append(name)
            serializer = getMultiAdapter(
                (field, factory.schema, self.request),
                ISchemaFieldSerializeToJson)
            result['properties'][name] = serializer()

            invariants = []
            for i in factory.schema.queryTaggedValue('invariants', []):
                invariants.append("%s.%s" % (i.__module__, i.__name__))
            result['invariants'] = invariants

        # Behavior serialization
        for schema in factory.behaviors or ():

            schema_serializer = getMultiAdapter(
                (schema, factory, self.request), ISchemaSerializeToJson)

            serialization = schema_serializer()
            result['properties'][schema_serializer.name] = \
                {'$ref': '#/definitions/' + schema_serializer.name},
            result['definitions'][schema_serializer.name] = serialization

        return result


@adapter(Interface, IFactory, Interface)
@implementer(ISchemaSerializeToJson)
class DefaultSchemaSerializer(object):

    def __init__(self, schema, factory, request):
        self.schema = schema
        self.factory = factory
        self.request = request
        self.schema_json = {
            'type': 'object',
            'properties': {},
            'required': [],
            'invariants': []
        }

    def __call__(self):
        for name, field in getFieldsInOrder(self.schema):
            serializer = getMultiAdapter(
                (field, self.schema, self.request),
                ISchemaFieldSerializeToJson)
            self.schema_json['properties'][name] = serializer()
            if field.required:
                self.schema_json['required'].append(name)
        self.schema_json['invariants'] = self.invariants

        return self.schema_json

    @property
    def name(self):
        return self.schema.__name__

    @property
    def invariants(self):
        invariants = []
        for i in self.schema.queryTaggedValue('invariants', []):
            invariants.append("%s.%s" % (i.__module__, i.__name__))
        return invariants
