# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.component.interfaces import IFactory
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IRequest
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.profile import profilable
from guillotina.schema import get_fields_in_order
from zope.interface import Interface


@configure.adapter(
    for_=(IFactory, IRequest),
    provides=IFactorySerializeToJson)
class SerializeFactoryToJson(object):

    def __init__(self, factory, request):
        self.factory = factory
        self.request = request

    @profilable
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
        for name, field in get_fields_in_order(factory.schema):
            if field.required:
                result['required'].append(name)
            serializer = get_multi_adapter(
                (field, factory.schema, self.request),
                ISchemaFieldSerializeToJson)
            result['properties'][name] = await serializer()

            invariants = []
            for i in factory.schema.queryTaggedValue('invariants', []):
                invariants.append("%s.%s" % (i.__module__, i.__name__))
            result['invariants'] = invariants

        # Behavior serialization
        for schema in factory.behaviors or ():
            schema_serializer = get_multi_adapter(
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
        for name, field in get_fields_in_order(self.schema):
            serializer = get_multi_adapter(
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
