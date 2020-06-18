from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import get_adapter
from guillotina.event import notify
from guillotina.events import RegistryEditedEvent
from guillotina.exceptions import ComponentLookupError
from guillotina.i18n import MessageFactory
from guillotina.interfaces import IContainer
from guillotina.interfaces import IJSONToValue
from guillotina.json.serialize_value import json_compatible
from guillotina.response import ErrorResponse
from guillotina.response import HTTPNotFound
from guillotina.response import Response
from guillotina.schema import get_fields
from guillotina.schema.exceptions import ValidationError
from guillotina.utils import get_registry
from guillotina.utils import import_class
from guillotina.utils import resolve_dotted_name


_ = MessageFactory("guillotina")


_marker = object()


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.ReadConfiguration",
    name="@registry/{key}",
    summary="Read container registry settings",
    parameters=[{"in": "path", "name": "key", "required": True, "schema": {"type": "string"}}],
    responses={
        "200": {
            "description": "Successfully registered interface",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"value": {"type": "object"}}}
                }
            },
        }
    },
)
class Read(Service):
    async def prepare(self):
        # we want have the key of the registry
        self.key = self.request.matchdict["key"]
        registry = await get_registry(self.context)
        self.value = registry.get(self.key, _marker)
        if self.value is _marker:
            raise HTTPNotFound(content={"message": f"{self.key} not in settings"})

    async def __call__(self):
        try:
            result = json_compatible(self.value)
        except (ComponentLookupError, TypeError):
            result = self.value
        return {"value": result}


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.ReadConfiguration",
    name="@registry",
    summary="Read container registry settings",
    responses={
        "200": {
            "description": "Successfully registered interface",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"value": {"type": "object"}}}
                }
            },
        }
    },
)
async def get_registry_service(context, request):
    result = {}
    registry = await get_registry(context)
    for key in registry.keys():
        try:
            value = json_compatible(registry[key])
        except (ComponentLookupError, TypeError):
            value = registry[key]
        result[key] = value
    return {"value": result}


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.RegisterConfigurations",
    name="@registry",
    summary="Register a new interface to for registry settings",
    validate=True,
    requestBody={
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "title": "Registry",
                    "properties": {"interface": {"type": "string"}, "initial_values": {"type": "object"}},
                    "required": ["interface"],
                }
            }
        },
    },
    responses={"200": {"description": "Successfully registered interface"}},
)
class Register(Service):
    """Register an Interface on the Registry."""

    async def __call__(self):
        """ data input : { 'interface': 'INTERFACE' }"""
        registry = await get_registry()
        if registry is None:
            return ErrorResponse("BadRequest", _("Not in a container request"), status=412)

        data = await self.request.json()
        interface = data.get("interface", None)
        initial_values = data.get("initial_values", {})
        if interface is None:
            return ErrorResponse("InvalidRequest", "Non existent Interface", status=412)

        iObject = import_class(interface)
        registry.register_interface(iObject)
        config = registry.for_interface(iObject)

        # Initialize values
        # If its defined on the guillotina.schema default will not be overwritten
        #  you will need to PATCH
        for key, field in get_fields(iObject).items():
            if key in initial_values and getattr(config, key, _marker) == _marker:
                # We don't have a value
                config[key] = initial_values[key]

        await notify(RegistryEditedEvent(self.context, registry, {interface: initial_values}))

        return Response(status=201)


@configure.service(
    context=IContainer,
    method="PATCH",
    permission="guillotina.WriteConfiguration",
    name="@registry/{dotted_name}",
    summary="Update registry setting",
    validate=True,
    parameters=[{"in": "path", "name": "dotter_name", "required": True, "schema": {"type": "string"}}],
    requestBody={
        "required": True,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UpdateRegistry"}}},
    },
    responses={"200": {"description": "Successfully wrote configuration"}},
)
class Write(Service):
    key = _marker
    value = None

    async def prepare(self):
        self.key = self.request.matchdict["dotted_name"]
        registry = await get_registry()
        self.value = registry.get(self.key)

    async def __call__(self):
        if self.key is _marker:
            # No option to write the root of registry
            return ErrorResponse("InvalidRequest", "Needs the registry key", status=412)

        data = await self.request.json()
        if "value" in data:
            value = data["value"]
        else:
            value = data

        assert "." in self.key, "Registry key must be dotted.iface.name.fieldname"  # noqa
        iface_name, name = self.key.rsplit(".", 1)
        iface = resolve_dotted_name(iface_name)

        assert iface is not None, "Must provide valid registry interface"  # noqa
        try:
            field = iface[name]
        except KeyError:
            return ErrorResponse(
                "DeserializationError", "Invalid field name {}".format(str(name)), status=412
            )

        try:
            new_value = get_adapter((field), IJSONToValue, args=[value, self.context])
        except ComponentLookupError:
            return ErrorResponse(
                "DeserializationError", "Cannot deserialize type {}".format(str(self.field)), status=412
            )
        except ValidationError as e:
            return ErrorResponse("ValidationError", "Invalid value type {}".format(str(e)), status=412)

        registry = await get_registry()
        registry[self.key] = new_value

        await notify(RegistryEditedEvent(self.context, registry, {iface_name: {name: value}}))

        return Response(status=204)
