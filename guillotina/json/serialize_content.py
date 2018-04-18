# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import get_multi_adapter
from guillotina.component import query_utility
from guillotina.content import get_all_behaviors
from guillotina.content import get_cached_factory
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import read_permission
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IFolder
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPermission
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceSerializeToJson
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.json.serialize_value import json_compatible
from guillotina.profile import profilable
from guillotina.schema import get_fields
from guillotina.utils import apply_coroutine
from zope.interface import Interface

import logging


logger = logging.getLogger('guillotina')


MAX_ALLOWED = 20


@configure.adapter(
    for_=(IResource, Interface),
    provides=IResourceSerializeToJson)
class SerializeToJson(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.permission_cache = {}

    @profilable
    async def __call__(self, include=[], omit=[]):
        self.include = include
        self.omit = omit

        parent = self.context.__parent__
        if parent is not None:
            # We render the summary of the parent
            try:
                parent_summary = await get_multi_adapter(
                    (parent, self.request), IResourceSerializeToJsonSummary)()
            except ComponentLookupError:
                parent_summary = {}
        else:
            parent_summary = {}

        result = {
            '@id': IAbsoluteURL(self.context, self.request)(),
            '@type': self.context.type_name,
            '@name': self.context.__name__,
            '@uid': self.context.uuid,
            'parent': parent_summary,
            'creation_date': json_compatible(self.context.creation_date),
            'modification_date': json_compatible(self.context.modification_date),
            'UID': self.context.uuid,
        }

        factory = get_cached_factory(self.context.type_name)

        main_schema = factory.schema
        await self.get_schema(main_schema, self.context, result, False)

        # include can be one of:
        # - <field name> on content schema
        # - namespace.IBehavior
        # - namespace.IBehavior.field_name
        included_ifaces = [name for name in self.include if '.' in name]
        included_ifaces.extend([name.rsplit('.', 1)[0] for name in self.include
                                if '.' in name])
        for behavior_schema, behavior in await get_all_behaviors(self.context, load=False):
            dotted_name = behavior_schema.__identifier__
            if (dotted_name in self.omit or
                    (len(included_ifaces) > 0 and dotted_name not in included_ifaces)):
                # make sure the schema isn't filtered
                continue
            if (not getattr(behavior, 'auto_serialize', True) and
                    dotted_name not in included_ifaces):
                continue
            if IAsyncBehavior.implementedBy(behavior.__class__):
                # providedBy not working here?
                await behavior.load(create=False)
            await self.get_schema(behavior_schema, behavior, result, True)

        return result

    @profilable
    async def get_schema(self, schema, context, result, behavior):
        read_permissions = merged_tagged_value_dict(schema, read_permission.key)
        schema_serial = {}
        for name, field in get_fields(schema).items():

            if not self.check_permission(read_permissions.get(name)):
                continue

            if behavior:
                # omit/include for behaviors need full name
                dotted_name = schema.__identifier__ + '.' + name
            else:
                dotted_name = name
            if (dotted_name in self.omit or (
                    len(self.include) > 0 and (
                        dotted_name not in self.include and
                        schema.__identifier__ not in self.include))):
                # make sure the fields aren't filtered
                continue

            value = await self.serialize_field(context, field)
            if not behavior:
                result[name] = value
            else:
                schema_serial[name] = value

        if behavior and len(schema_serial) > 0:
            result[schema.__identifier__] = schema_serial

    @profilable
    async def serialize_field(self, context, field, default=None):
        try:
            value = await apply_coroutine(field.get, context)
        except Exception:
            logger.warning(f'Could not find value for schema field'
                           f'({self.field.__name__}), falling back to getattr')
            value = getattr(context, field.__name__, default)
        return json_compatible(value)

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = query_utility(IPermission,
                                       name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                security = IInteraction(self.request)
                self.permission_cache[permission_name] = bool(
                    security.check_permission(permission.id, self.context))
        return self.permission_cache[permission_name]


@configure.adapter(
    for_=(IFolder, Interface),
    provides=IResourceSerializeToJson)
class SerializeFolderToJson(SerializeToJson):

    @profilable
    async def __call__(self, include=[], omit=[]):
        result = await super(SerializeFolderToJson, self).__call__(include=include, omit=omit)

        security = IInteraction(self.request)
        length = await self.context.async_len()

        if length > MAX_ALLOWED or length == 0:
            result['items'] = []
        else:
            result['items'] = []
            async for ident, member in self.context.async_items(suppress_events=True):
                if not ident.startswith('_') and bool(
                        security.check_permission(
                        'guillotina.AccessContent', member)):
                    result['items'].append(
                        await get_multi_adapter(
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
            '@name': self.context.__name__,
            '@type': self.context.type_name,
            '@uid': self.context.uuid,
            'UID': self.context.uuid
        })
        return summary
