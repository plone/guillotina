# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import getMultiAdapter
from guillotina.component import queryMultiAdapter
from guillotina.component import queryUtility
from guillotina.content import get_all_behaviors
from guillotina.content import get_cached_factory
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import read_permission
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IFolder
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPermission
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFieldSerializer
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.json.serialize_value import json_compatible
from guillotina.schema import getFields
from zope.interface import Interface


MAX_ALLOWED = 200


@configure.adapter(
    for_=(IResource, Interface),
    provides=IResourceSerializeToJson)
class SerializeToJson(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.permission_cache = {}

    async def __call__(self):
        parent = self.context.__parent__
        if parent is not None:
            # We render the summary of the parent
            try:
                parent_summary = await getMultiAdapter(
                    (parent, self.request), IResourceSerializeToJsonSummary)()
            except ComponentLookupError:
                parent_summary = {}
        else:
            parent_summary = {}

        result = {
            '@id': IAbsoluteURL(self.context, self.request)(),
            '@type': self.context.type_name,
            'parent': parent_summary,
            'creation_date': json_compatible(self.context.creation_date),
            'modification_date': json_compatible(self.context.modification_date),
            'UID': self.context.uuid,
        }

        factory = get_cached_factory(self.context.type_name)

        main_schema = factory.schema
        await self.get_schema(main_schema, self.context, result, False)

        for behavior_schema, behavior in await get_all_behaviors(self.context):
            await self.get_schema(behavior_schema, behavior, result, True)

        return result

    async def get_schema(self, schema, context, result, behavior):
        read_permissions = merged_tagged_value_dict(schema, read_permission.key)
        schema_serial = {}
        for name, field in getFields(schema).items():

            if not self.check_permission(read_permissions.get(name)):
                continue
            serializer = queryMultiAdapter(
                (field, context, self.request),
                IResourceFieldSerializer)
            value = await serializer()
            if not behavior:
                result[name] = value
            else:
                schema_serial[name] = value

        if behavior:
            result[schema.__identifier__] = schema_serial

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = queryUtility(IPermission,
                                      name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                security = IInteraction(self.request)
                self.permission_cache[permission_name] = bool(
                    security.check_permission(permission.title, self.context))
        return self.permission_cache[permission_name]


@configure.adapter(
    for_=(IFolder, Interface),
    provides=IResourceSerializeToJson)
class SerializeFolderToJson(SerializeToJson):

    async def __call__(self):
        result = await super(SerializeFolderToJson, self).__call__()

        security = IInteraction(self.request)
        length = await self.context.async_len()

        if length > MAX_ALLOWED or length == 0:
            result['items'] = []
        else:
            result['items'] = []
            async for ident, member in self.context.async_items():
                if not ident.startswith('_') and bool(
                        security.check_permission(
                        'guillotina.AccessContent', member)):
                    result['items'].append(
                        await getMultiAdapter(
                            (member, self.request),
                            IResourceSerializeToJsonSummary)())
        result['length'] = length

        return result


@configure.adapter(
    for_=(IResource, Interface),
    provides=IResourceSerializeToJsonSummary)
class DefaultJSONSummarySerializer(object):
    """Default ISerializeToJsonSummary adapter.

    Requires context to be adaptable to IContentListingObject, which is
    the case for all content objects providing IResource.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    async def __call__(self):

        summary = json_compatible({
            '@id': IAbsoluteURL(self.context)(),
            '@type': self.context.type_name
        })
        return summary
