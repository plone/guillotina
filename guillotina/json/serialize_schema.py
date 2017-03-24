# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.component.interfaces import IFactory
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IRequest
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.schema import getFieldsInOrder
from zope.interface import Interface


@configure.adapter(
    for_=(IFactory, IRequest),
    provides=IFactorySerializeToJson)
class SerializeFactoryToJson(object):

    def __init__(self, factory, request):
        self.factory = factory
        self.request = request

    async def __call__(self):
        factory = self.factory
        result = {
            'title': factory.type_name,
            '$schema': 'http://json-schema.org/draft-04/schema#',
            'type': 'object',
            'required': [],
            'definitions': {},
            'properties': {}
        }

        # Base object class serialized
        for name, field in getFieldsInOrder(factory.schema):
            if field.required:
                result['required'].append(name)
            serializer = getMultiAdapter(
                (field, factory.schema, self.request),
                ISchemaFieldSerializeToJson)
            result['properties'][name] = await serializer()

            invariants = []
            for i in factory.schema.queryTaggedValue('invariants', []):
                invariants.append("%s.%s" % (i.__module__, i.__name__))
            result['invariants'] = invariants

        # Behavior serialization
        for schema in factory.behaviors or ():
            schema_serializer = getMultiAdapter(
                (schema, self.request), ISchemaSerializeToJson)

            serialization = await schema_serializer()
            result['properties'][schema_serializer.name] = \
                {'$ref': '#/definitions/' + schema_serializer.name},
            result['definitions'][schema_serializer.name] = serialization

        return result


@configure.adapter(
    for_=(Interface, Interface),
    provides=ISchemaSerializeToJson)
class DefaultSchemaSerializer(object):

    def __init__(self, schema, request):
        self.schema = schema
        self.request = request
        self.schema_json = {
            'type': 'object',
            'properties': {},
            'required': [],
            'invariants': []
        }

    async def __call__(self):
        for name, field in getFieldsInOrder(self.schema):
            serializer = getMultiAdapter(
                (field, self.schema, self.request),
                ISchemaFieldSerializeToJson)
            self.schema_json['properties'][name] = await serializer()
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
