# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import get_multi_adapter
from guillotina.component import get_utility
from guillotina.component.interfaces import IFactory
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IFactorySerializeToJson
from guillotina.interfaces import IRequest
from guillotina.interfaces import ISchemaFieldSerializeToJson
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.profile import profilable
from guillotina.schema import get_fields_in_order
from zope.interface import Interface


@configure.adapter(for_=(IFactory, IRequest), provides=IFactorySerializeToJson)
class SerializeFactoryToJson(object):
    def __init__(self, factory, request):
        self.factory = factory
        self.request = request

    @profilable
    async def __call__(self):
        factory = self.factory
        result = {
            "title": factory.type_name,
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "components": {"schemas": {}},
            "properties": {},
        }
        required = []

        # Base object class serialized
        for name, field in get_fields_in_order(factory.schema):
            if field.required:
                required.append(name)
            serializer = get_multi_adapter((field, factory.schema, self.request), ISchemaFieldSerializeToJson)
            result["properties"][name] = await serializer()
        if len(required) > 0:
            result["required"] = required

        # Behavior serialization
        for schema in factory.behaviors or ():
            schema_serializer = get_multi_adapter((schema, self.request), ISchemaSerializeToJson)

            serialization = await schema_serializer()
            result["properties"][schema_serializer.name] = {
                "$ref": "#/components/schemas/" + schema_serializer.name
            }
            behavior = get_utility(IBehavior, name=schema_serializer.name)
            serialization["title"] = behavior.title or schema_serializer.short_name
            serialization["description"] = behavior.description

            result["components"]["schemas"][schema_serializer.name] = serialization

        return result


@configure.adapter(for_=(Interface, Interface), provides=ISchemaSerializeToJson)
class DefaultSchemaSerializer(object):
    def __init__(self, schema, request):
        self.schema = schema
        self.request = request

    async def __call__(self):
        return self.serialize()

    def serialize(self):
        result = {"type": "object", "properties": {}}
        required = []
        for name, field in get_fields_in_order(self.schema):
            serializer = get_multi_adapter((field, self.schema, self.request), ISchemaFieldSerializeToJson)
            result["properties"][name] = serializer.serialize()
            if field.required:
                required.append(name)

        if len(required) > 0:
            result["required"] = required
        return result

    @property
    def name(self):
        return self.schema.__identifier__

    @property
    def short_name(self):
        return self.schema.__name__
