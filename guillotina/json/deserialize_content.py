# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina import glogging
from guillotina.component import ComponentLookupError
from guillotina.component import get_adapter
from guillotina.component import query_utility
from guillotina.content import get_all_behaviors
from guillotina.content import get_cached_factory
from guillotina.db.transaction import _EMPTY
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import write_permission
from guillotina.exceptions import DeserializationError
from guillotina.exceptions import Invalid
from guillotina.exceptions import NoInteraction
from guillotina.exceptions import ValueDeserializationError
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IInteraction
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IPermission
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import RESERVED_ATTRS
from guillotina.schema import get_fields
from guillotina.schema.exceptions import ValidationError
from guillotina.utils import apply_coroutine
from zope.interface import Interface

import asyncio


logger = glogging.getLogger('guillotina')
_missing = object()


@configure.adapter(
    for_=(IResource, Interface),
    provides=IResourceDeserializeFromJson)
class DeserializeFromJson(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.permission_cache = {}

    async def __call__(self, data, validate_all=False, ignore_errors=False, create=False):
        errors = []

        # do behavior first in case they modify context values
        for behavior_schema, behavior in await get_all_behaviors(self.context, load=False):
            dotted_name = behavior_schema.__identifier__
            if dotted_name not in data:
                # syntax {"namespace.IBehavior": {"foo": "bar"}}
                # we're not even patching this behavior if no iface found in payload
                if create:
                    # signal to caching engine to cache no data here so
                    # we prevent a future lookup
                    try:
                        txn = self.context._p_jar
                        await txn._cache.set(
                            _EMPTY, container=self.context,
                            id=behavior.__annotations_data_key__,
                            variant='annotation')
                    except AttributeError:
                        pass
                continue
            if IAsyncBehavior.implementedBy(behavior.__class__):
                # providedBy not working here?
                await behavior.load(create=True)
            await self.set_schema(
                behavior_schema, behavior, data, errors,
                validate_all, True)

        factory = get_cached_factory(self.context.type_name)
        main_schema = factory.schema
        await self.set_schema(
            main_schema, self.context, data, errors, validate_all, False)

        if errors and not ignore_errors:
            raise DeserializationError(errors)

        self.context._p_register()

        return self.context

    async def set_schema(
            self, schema, obj, data, errors,
            validate_all=False, behavior=False):
        write_permissions = merged_tagged_value_dict(schema, write_permission.key)

        for name, field in get_fields(schema).items():
            if name in RESERVED_ATTRS:
                continue

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

                try:
                    value = await self.get_value(f, obj, data_value)
                except ValueError as e:
                    errors.append({
                        'message': 'Value error', 'field': name, 'error': e})
                except ValidationError as e:
                    errors.append({
                        'message': e.doc(), 'field': name, 'error': e})
                except ValueDeserializationError as e:
                    errors.append({
                        'message': e.message, 'field': name, 'error': e})
                except Invalid as e:
                    errors.append({
                        'message': e.args[0], 'field': name, 'error': e})
                else:
                    # record object changes for potential future conflict resolution
                    try:
                        await apply_coroutine(field.set, obj, value)
                    except ValidationError as e:
                        errors.append({
                            'message': e.doc(), 'field': name, 'error': e})
                    except ValueDeserializationError as e:
                        errors.append({
                            'message': e.message, 'field': name, 'error': e})
                    except AttributeError:
                        logger.warning(
                            f'AttributeError setting data on field {name}', exc_info=True)
                    except Exception:
                        if not isinstance(getattr(type(obj), name, None), property):
                            # we can not set data on properties
                            logger.warning(
                                'Error setting data on field, falling back to setattr',
                                exc_info=True)
                            setattr(obj, name, value)
                        else:
                            logger.warning(
                                'Error setting data on field', exc_info=True)
            else:
                if validate_all and f.required and not hasattr(obj, name):
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
                for error in validation:
                    errors.append({
                        'message': error[1].doc(),
                        'field': error[0],
                        'error': error
                    })

    async def get_value(self, field, obj, value):
        if value is None:
            return None
        try:
            value = get_adapter(field, IJSONToValue, args=[value, obj])
            if asyncio.iscoroutine(value):
                value = await value
            field.validate(value)
            return value
        except ComponentLookupError:
            raise ValueDeserializationError(
                field, value, 'Deserializer not found for field')

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = query_utility(IPermission,
                                       name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                try:
                    self.permission_cache[permission_name] = bool(
                        IInteraction(self.request).check_permission(
                            permission.id, self.context))
                except NoInteraction:
                    # not authenticated
                    return False
        return self.permission_cache[permission_name]
