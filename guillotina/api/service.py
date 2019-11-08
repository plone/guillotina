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


class Service(View):
    __validator__ = __schema__ = __original__ = None

    def _validate_parameters(self):
        if "parameters" in self.__config__:
            data = self.request.url.query
            for parameter in self.__config__["parameters"]:
                if parameter["in"] == "query":
                    if "schema" in parameter and "name" in parameter:
                        if parameter["schema"]["type"] == "integer":
                            try:
                                int(data[parameter["name"]])
                            except ValueError:
                                raise HTTPPreconditionFailed(
                                    content={
                                        "reason": "Schema validation error",
                                        "message": "can not convert {} to Int".format(
                                            data[parameter["name"]]
                                        ),
                                    }
                                )
                        elif parameter["schema"]["type"] == "float":
                            try:
                                float(data[parameter["name"]])
                            except ValueError:
                                raise HTTPPreconditionFailed(
                                    content={
                                        "reason": "Schema validation error",
                                        "message": "can not convert {} to Float".format(
                                            data[parameter["name"]]
                                        ),
                                    }
                                )
                        else:
                            pass
                        try:
                            if parameter.get("required", False) and parameter["name"] not in data:
                                raise HTTPPreconditionFailed(
                                    content={
                                        "reason": "Schema validation error",
                                        "message": "{} is required".format(parameter["name"]),
                                    }
                                )
                        except KeyError:
                            logger.warning("`required` is a mandatory field", exc_info=True)

    @classmethod
    def _get_validator(cls):
        if cls.__validator__ is None and cls.__validator__ != _sentinal:
            cls.__validator__ = _sentinal
            if "requestBody" in cls.__config__:
                requestBody = cls.__config__["requestBody"]
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
                    except KeyError:
                        logger.warning("Invalid jsonschema", exc_info=True)
                elif schema is not None:
                    try:
                        cls.__schema__ = schema
                        jsonschema_validator = jsonschema.validators.validator_for(cls.__schema__)
                        cls.__validator__ = jsonschema_validator(cls.__schema__)
                    except jsonschema.exceptions.ValidationError:
                        logger.warning("Could not validate schema", exc_info=True)
                else:
                    logger.warning("No schema found in service definition")
            else:
                pass  # can be used for query, path or header parameters
        return cls.__schema__, cls.__validator__

    async def _call_validate(self):
        self._validate_parameters()
        schema, validator = self.__class__._get_validator()
        if validator and validator != _sentinal:
            try:
                data = await self.request.json()
                validator.validate(data)
            except jsonschema.exceptions.ValidationError as e:
                raise HTTPPreconditionFailed(
                    content={
                        "reason": "json schema validation error",
                        "message": e.message,
                        "validator": e.validator,
                        "validator_value": e.validator_value,
                        "path": [i for i in e.path],
                        "schema_path": [i for i in e.schema_path],
                        "schema": schema,
                    }
                )
        return await self._call_original()

    async def _call_original(self):
        return await self.__original__()

    async def _call_original_func(self):
        return await self.__original__(self.context, self.request)

    async def get_data(self):
        return await self.request.json()


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
