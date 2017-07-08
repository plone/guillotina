# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import queryMultiAdapter
from guillotina.component import queryUtility
from guillotina.content import get_all_behaviors
from guillotina.content import get_cached_factory
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import write_permission
from guillotina.exceptions import NoInteraction
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IPermission
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import IResourceFieldDeserializer
from guillotina.json.exceptions import DeserializationError
from guillotina.schema import getFields
from guillotina.schema.exceptions import ValidationError
from guillotina.utils import apply_coroutine
from zope.interface import Interface
from zope.interface.exceptions import Invalid

import logging


logger = logging.getLogger('guillotina')
_missing = object()


@configure.adapter(
    for_=(IResource, Interface),
    provides=IResourceDeserializeFromJson)
class DeserializeFromJson(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.permission_cache = {}

    async def __call__(self, data, validate_all=False, ignore_errors=False):
        errors = []

        factory = get_cached_factory(self.context.type_name)
        main_schema = factory.schema
        await self.set_schema(
            main_schema, self.context, data, errors, validate_all, False)

        for behavior_schema, behavior in await get_all_behaviors(self.context, True):
            await self.set_schema(
                behavior_schema, behavior, data, errors,
                validate_all, True)

        if errors and not ignore_errors:
            raise DeserializationError(errors)

        self.context._p_register()

        return self.context

    async def set_schema(
            self, schema, obj, data, errors,
            validate_all=False, behavior=False):
        write_permissions = merged_tagged_value_dict(schema, write_permission.key)

        for name, field in getFields(schema).items():

            if field.readonly:
                continue

            if behavior:
                found = False
                if schema.__identifier__ in data:
                    sdata = data[schema.__identifier__]
                    data_value = sdata[name] if name in sdata else None
                    found = True if name in sdata else False
            else:
                data_value = data[name] if name in data else None
                found = True if name in data else False

            f = schema.get(name)
            if found:

                if not self.check_permission(write_permissions.get(name)):
                    continue

                # Deserialize to field value
                deserializer = queryMultiAdapter(
                    (f, obj, self.request),
                    IResourceFieldDeserializer)
                if deserializer is None:
                    continue

                try:
                    value = deserializer(data_value)
                except ValueError as e:
                    errors.append({
                        'message': e.message, 'field': name, 'error': e})
                except ValidationError as e:
                    errors.append({
                        'message': e.doc(), 'field': name, 'error': e})
                except Invalid as e:
                    errors.append({
                        'message': e.args[0], 'field': name, 'error': e})
                else:
                    # record object changes for potential future conflict resolution
                    try:
                        await apply_coroutine(field.set, obj, value)
                    except Exception:
                        logger.warning(
                            'Error setting data on field, falling back to setattr',
                            exc_info=True)
                        setattr(obj, name, value)
            else:
                if f.required and not hasattr(obj, name):
                    errors.append({
                        'message': 'Required parameter', 'field': name,
                        'error': ValueError('Required parameter')})

        if validate_all:
            invariant_errors = []
            try:
                schema.validateInvariants(object, invariant_errors)
            except Invalid:
                # Just collect errors
                pass
            validation = [(None, e) for e in invariant_errors]

            if len(validation):
                for e in validation:
                    errors.append({
                        'message': e[1].doc(),
                        'field': e[0],
                        'error': e
                    })

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = queryUtility(IPermission,
                                      name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                try:
                    self.permission_cache[permission_name] = bool(
                        IInteraction(self.request).check_permission(
                            permission.title, self.context))
                except NoInteraction:
                    # not authenticated
                    return False
        return self.permission_cache[permission_name]
