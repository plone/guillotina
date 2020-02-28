# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina import glogging
from guillotina.component import ComponentLookupError
from guillotina.component import get_adapter
from guillotina.component import query_utility
from guillotina.content import get_all_behaviors
from guillotina.content import get_cached_factory
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.transaction import _EMPTY
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import write_permission
from guillotina.exceptions import DeserializationError
from guillotina.exceptions import Invalid
from guillotina.exceptions import Unauthorized
from guillotina.exceptions import ValueDeserializationError
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IJSONToValue
from guillotina.interfaces import IPermission
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.interfaces import RESERVED_ATTRS
from guillotina.interfaces.misc import IRequest
from guillotina.json.utils import validate_invariants
from guillotina.schema import get_fields
from guillotina.schema.exceptions import ValidationError
from guillotina.schema.interfaces import IField
from guillotina.utils import apply_coroutine
from guillotina.utils import get_security_policy
from typing import Any
from typing import Dict
from typing import List
from typing import Type
from zope.interface import Interface

import asyncio


logger = glogging.getLogger("guillotina")
_missing = object()


@configure.adapter(for_=(IResource, Interface), provides=IResourceDeserializeFromJson)
class DeserializeFromJson(object):
    def __init__(self, context: IBaseObject, request: IRequest):
        self.context = context
        self.request = request

        self.permission_cache: Dict[str, bool] = {}

    async def __call__(
        self,
        data: Dict[str, Any],
        validate_all: bool = False,
        ignore_errors: bool = False,
        create: bool = False,
    ) -> IBaseObject:
        errors: List[Dict[str, Any]] = []

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
                        txn = self.context.__txn__
                        await txn._cache.set(
                            _EMPTY,
                            container=self.context,
                            id=behavior.__annotations_data_key__,
                            variant="annotation",
                        )
                    except AttributeError:
                        pass
                continue
            if IAsyncBehavior.implementedBy(behavior.__class__):
                # providedBy not working here?
                await behavior.load(create=True)
            await self.set_schema(behavior_schema, behavior, data, errors, validate_all, True)

        factory = get_cached_factory(self.context.type_name)
        main_schema = factory.schema
        await self.set_schema(main_schema, self.context, data, errors, validate_all, False)

        if errors and not ignore_errors:
            raise DeserializationError(errors)

        return self.context

    async def set_schema(
        self,
        schema: Type[Interface],
        obj: IBaseObject,
        data: Dict[str, Any],
        errors: List[Dict[str, Any]],
        validate_all: bool = False,
        behavior: bool = False,
    ):
        write_permissions = merged_tagged_value_dict(schema, write_permission.key)
        changed = False
        for name, field in get_fields(schema).items():

            if name in RESERVED_ATTRS:
                continue

            if field.readonly:
                continue

            if behavior:
                found = False
                if data.get(schema.__identifier__):
                    sdata = data[schema.__identifier__]
                    data_value = sdata[name] if name in sdata else None
                    found = True if name in sdata else False
            else:
                data_value = data[name] if name in data else None
                found = True if name in data else False
            if found:

                if not self.check_permission(write_permissions.get(name)):
                    raise Unauthorized("Write permission not allowed")

                try:
                    field = field.bind(obj)
                    value = await self.get_value(field, obj, data_value)
                except ValueError as e:
                    errors.append({"message": "Value error", "field": name, "error": e})
                except ValidationError as e:
                    errors.append({"message": e.doc(), "field": name, "error": e, "details": str(e)})
                except ValueDeserializationError as e:
                    errors.append({"message": e.message, "field": name, "error": e})
                except Invalid as e:
                    errors.append({"message": e.args[0], "field": name, "error": e})
                else:
                    # record object changes for potential future conflict resolution
                    try:
                        await apply_coroutine(field.set, obj, value)
                        changed = True
                    except ValidationError as e:
                        errors.append({"message": e.doc(), "field": name, "error": e, "details": str(e)})
                    except ValueDeserializationError as e:
                        errors.append({"message": e.message, "field": name, "error": e})
                    except AttributeError:
                        logger.warning(f"AttributeError setting data on field {name}", exc_info=True)
                    except Exception:
                        logger.warning(
                            f"Unhandled error setting data on field, {schema} {name}", exc_info=True
                        )
                        errors.append(
                            {
                                "message": "Unhandled exception",
                                "field": name,
                                "error": ValueDeserializationError(field, value, "Unhandled error"),
                            }
                        )
            else:
                if validate_all and field.required and getattr(obj, name, None) is None:
                    errors.append(
                        {
                            "message": "Required parameter",
                            "field": name,
                            "error": ValueError("Required parameter"),
                        }
                    )

        for error in await validate_invariants(schema, obj):
            if isinstance(error, ValidationError):
                errors.append(
                    {
                        "message": error.doc(),
                        "value": error.value,
                        "field": error.field_name,
                        "error": error.errors,
                    }
                )
            else:
                if len(getattr(error, "args", [])) > 0 and isinstance(error.args[0], str):
                    message = error.args[0]
                else:
                    message = error.__doc__
                errors.append({"message": message, "error": error})

        if changed:
            obj.register()

    async def get_value(self, field: IField, obj: IBaseObject, value: Any) -> Any:
        try:
            if value is not None:
                value = get_adapter(field, IJSONToValue, args=[value, obj])
                if asyncio.iscoroutine(value):
                    value = await value
            field.validate(value)
            return value
        except ComponentLookupError:
            raise ValueDeserializationError(field, value, "Deserializer not found for field")

    def check_permission(self, permission_name: str) -> bool:
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = query_utility(IPermission, name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                self.permission_cache[permission_name] = bool(
                    get_security_policy().check_permission(permission.id, self.context)
                )
        return self.permission_cache[permission_name]
