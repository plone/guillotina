from guillotina import glogging
from guillotina._cache import BEHAVIOR_CACHE
from guillotina._settings import app_settings
from guillotina.browser import View
from guillotina.component import query_utility
from guillotina.component.interfaces import IFactory
from guillotina.fields import CloudFileField
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import ICloudFileField
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPPreconditionFailed
from guillotina.schema import Dict
from guillotina.utils import get_schema_validator
from guillotina.utils import JSONSchemaRefResolver
from typing import Any
from typing import Dict as TDict
from typing import List as TList
from typing import Union

import json
import jsonschema


logger = glogging.getLogger("guillotina")


class DictFieldProxy:
    def __init__(self, key, context, field_name):
        self.__key = key
        self.__context = context
        self.__field_name = field_name

    def __getattribute__(self, name):
        if name.startswith("_DictFieldProxy"):  # local attribute
            return super().__getattribute__(name)

        if name == self.__field_name:
            return getattr(self.__context, name).get(self.__key)
        else:
            return getattr(self.__context, name)

    def __setattr__(self, name, value):
        if name.startswith("_DictFieldProxy"):
            return super().__setattr__(name, value)

        if name == self.__field_name:
            val = getattr(self.__context, name)
            setattr(self.__context, name, val)
            val[self.__key] = value
        else:
            setattr(self.__context, name, value)


_sentinal = object()


def _safe_int_or_float_cast(value: Any) -> Union[int, float, Any]:
    if type(value) in (float, int):
        # No need to cast
        return value
    try:
        return int(value)
    except (ValueError, TypeError):
        # Could not cast to int
        try:
            return float(value)
        except (ValueError, TypeError):
            # Could not cast to float
            pass
    return value


class Service(View):
    __validator__ = __schema__ = __original__ = None
    __body_required__ = True

    def _validate_parameters(self):
        if "parameters" in self.__config__:
            data = self.request.url.query
            for parameter in self.__config__["parameters"]:
                if parameter["in"] != "query" or "schema" not in parameter or "name" not in parameter:
                    continue

                name = parameter["name"]
                if parameter.get("required") and name not in data:
                    raise HTTPPreconditionFailed(
                        content={
                            "reason": "Query schema validation error",
                            "message": "{} is required".format(parameter["name"]),
                            "path": [name],
                            "in": "query",
                            "parameter": name,
                            "schema": parameter["schema"],
                        }
                    )
                elif name not in data:
                    continue

                try:
                    if parameter["schema"].get("type") == "array":
                        value = data.getall(name)
                        if parameter["schema"].get("items", {}).get("type") in ("number", "integer"):
                            value = [_safe_int_or_float_cast(v) for v in value]
                    else:
                        value = data[name]
                        if parameter["schema"].get("type") in ("number", "integer"):
                            value = _safe_int_or_float_cast(value)

                    jsonschema.validate(instance=value, schema=parameter["schema"])
                except jsonschema.exceptions.ValidationError as e:
                    raise HTTPPreconditionFailed(
                        content={
                            "reason": "json schema validation error",
                            "message": e.message,
                            "validator": e.validator,
                            "validator_value": e.validator_value,
                            "path": [i for i in e.path],
                            "schema_path": [i for i in e.schema_path],
                            "parameter": name,
                            "in": "query",
                            "schema": parameter["schema"],
                        }
                    )

    @classmethod
    def _get_validator(cls):
        if cls.__validator__ is None and cls.__validator__ != _sentinal:
            cls.__validator__ = _sentinal
            if "requestBody" in cls.__config__:
                requestBody = cls.__config__["requestBody"]
                cls.__body_required__ = requestBody.get("required", True)
                try:
                    schema = requestBody["content"]["application/json"]["schema"]
                except KeyError:
                    return cls.__schema__, cls.__validator__
                if "$ref" in schema:
                    try:
                        ref = schema["$ref"]
                        schema_name = ref.split("/")[-1]
                        cls.__schema__ = app_settings["json_schema_definitions"][schema_name]
                        cls.__validator__ = get_schema_validator(schema_name)
                    except KeyError:  # pragma: no cover
                        logger.warning("Invalid jsonschema", exc_info=True)
                elif schema is not None:
                    try:
                        cls.__schema__ = schema
                        jsonschema_validator = jsonschema.validators.validator_for(cls.__schema__)
                        cls.__validator__ = jsonschema_validator(
                            cls.__schema__, resolver=JSONSchemaRefResolver.from_schema(schema)
                        )
                    except jsonschema.exceptions.ValidationError:  # pragma: no cover
                        logger.warning("Could not validate schema", exc_info=True)
            else:
                pass  # can be used for query, path or header parameters
        return cls.__schema__, cls.__validator__, cls.__body_required__

    async def _call_validate(self):
        self._validate_parameters()
        schema, validator, body_required = self.__class__._get_validator()
        if validator and validator != _sentinal:
            try:
                data = await self.request.json()
                validator.validate(data)
            except json.JSONDecodeError:
                if body_required:
                    raise
            except jsonschema.exceptions.ValidationError as e:
                raise HTTPPreconditionFailed(
                    content={
                        "reason": "json schema validation error",
                        "message": e.message,
                        "validator": e.validator,
                        "validator_value": e.validator_value,
                        "path": [i for i in e.path],
                        "schema_path": [i for i in e.schema_path],
                        "in": "body",
                        "schema": schema,
                    }
                )
        return await self._call_original()

    async def _call_original(self):
        return await self.__original__()

    async def _call_original_func(self):
        return await self.__original__(self.context, self.request)

    async def get_data(self) -> Union[TDict, TList]:
        body = await self.request.json()
        if not isinstance(body, list) and not isinstance(body, dict):
            # Technically, strings are also valid json payload...
            raise HTTPPreconditionFailed(content={"reason": "Invalid json payload"})
        return body


class DownloadService(Service):
    def __init__(self, context, request):
        super(DownloadService, self).__init__(context, request)


class TraversableFieldService(Service):
    field = None

    async def prepare(self):
        # we want have the field
        name = self.request.matchdict["field_name"]
        fti = query_utility(IFactory, name=self.context.type_name)
        schema = fti.schema
        field = None
        self.behavior = None
        if name in schema:
            field = schema[name]

        else:
            # TODO : We need to optimize and move to content.py iterSchema
            for behavior_schema in fti.behaviors or ():
                if name in behavior_schema:
                    field = behavior_schema[name]
                    self.behavior = behavior_schema(self.context)
                    break
            for behavior_name in self.context.__behaviors__ or ():
                behavior_schema = BEHAVIOR_CACHE[behavior_name]
                if name in behavior_schema:
                    field = behavior_schema[name]
                    self.behavior = behavior_schema(self.context)
                    break

        # Check that its a File Field
        if field is None:
            raise HTTPNotFound(content={"reason": "No valid name"})

        if self.behavior is not None:
            ctx = self.behavior
        else:
            ctx = self.context

        if self.behavior is not None and IAsyncBehavior.implementedBy(self.behavior.__class__):
            # providedBy not working here?
            await self.behavior.load()

        if type(field) == Dict:
            key = self.request.matchdict["filename"]
            self.field = CloudFileField(__name__=name).bind(DictFieldProxy(key, ctx, name))
        elif ICloudFileField.providedBy(field):
            self.field = field.bind(ctx)

        if self.field is None:
            raise HTTPNotFound(content={"reason": "No valid name"})

        return self
