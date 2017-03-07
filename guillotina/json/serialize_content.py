# -*- coding: utf-8 -*-
from guillotina import BEHAVIOR_CACHE
from guillotina import configure
from guillotina.content import get_cached_factory
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import read_permission
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IContainer
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFieldSerializer
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.json.serialize_value import json_compatible
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import Interface
from guillotina.schema import getFields
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPermission
import asyncio


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
                parent_summary = getMultiAdapter(
                    (parent, self.request), IResourceSerializeToJsonSummary)()
            except ComponentLookupError:
                parent_summary = {}
        else:
            parent_summary = {}

        result = {
            '@id': IAbsoluteURL(self.context, self.request)(),
            '@type': self.context.portal_type,
            'parent': parent_summary,
            'created': json_compatible(self.context.creation_date),
            'modified': json_compatible(self.context.modification_date),
            'UID': self.context.uuid,
        }

        factory = get_cached_factory(self.context.portal_type)

        main_schema = factory.schema
        await self.get_schema(main_schema, self.context, result, False)

        for behavior_schema in factory.behaviors or ():
            behavior = behavior_schema(self.context)
            await self.get_schema(behavior_schema, behavior, result, True)

        for dynamic_behavior in self.context.__behaviors__ or ():
            dynamic_behavior_obj = BEHAVIOR_CACHE[dynamic_behavior]
            behavior = dynamic_behavior_obj(self.context)
            await self.get_schema(dynamic_behavior_obj, behavior, result, True)

        return result

    async def get_schema(self, schema, context, result, behavior):
        read_permissions = merged_tagged_value_dict(schema, read_permission.key)
        schema_serial = {}
        for name, field in getFields(schema).items():

            if not self.check_permission(read_permissions.get(name)):
                continue
            serializer = await queryMultiAdapter(
                (field, context, self.request),
                IResourceFieldSerializer)
            value = serializer()
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
    for_=(IContainer, Interface),
    provides=IResourceSerializeToJson)
class SerializeFolderToJson(SerializeToJson):

    async def __call__(self):
        result = await super(SerializeFolderToJson, self).__call__()

        security = IInteraction(self.request)
        length = self.context.__len__()
        if asyncio.iscoroutine(length):
            length = await length

        if length > MAX_ALLOWED or length == 0:
            result['items'] = []
        else:
            items = self.context.items()
            # Needs to be a better way !
            if hasattr(items, 'ag_await'):
                result['items'] = []
                async for ident, member in items:
                    if not ident.startswith('_') and bool(
                            security.check_permission(
                            'guillotina.AccessContent', member)):
                        result['items'].append(
                            await getMultiAdapter(
                                (member, self.request),
                                IResourceSerializeToJsonSummary)()
                        )
            else:
                result['items'] = [
                    await getMultiAdapter(
                        (member, self.request), IResourceSerializeToJsonSummary)()
                    for ident, member in items
                    if not ident.startswith('_') and
                    bool(security.check_permission(
                        'guillotina.AccessContent', member))
                ]
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

    def __call__(self):

        summary = json_compatible({
            '@id': IAbsoluteURL(self.context)(),
            '@type': self.context.portal_type
        })
        return summary
