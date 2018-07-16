from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import get_adapter
from guillotina.exceptions import ComponentLookupError
from guillotina.exceptions import DeserializationError
from guillotina.i18n import MessageFactory
from guillotina.interfaces import IContainer
from guillotina.interfaces import IJSONToValue
from guillotina.json.serialize_value import json_compatible
from guillotina.response import ErrorResponse
from guillotina.response import HTTPNotFound
from guillotina.response import Response
from guillotina.schema import get_fields
from guillotina.utils import import_class
from guillotina.utils import resolve_dotted_name


_ = MessageFactory('guillotina')


_marker = object()


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.ReadConfiguration', name='@registry/{key}',
    summary='Read container registry settings',
    responses={
        "200": {
            "description": "Successfully registered interface",
            "type": "object",
            "schema": {
                "properties": {
                    "value": {
                        "type": "object"
                    }
                }
            }
        }
    })
class Read(Service):

    async def prepare(self):
        # we want have the key of the registry
        self.key = self.request.matchdict['key']
        self.value = self.request.container_settings.get(self.key, _marker)
        if self.value is _marker:
            raise HTTPNotFound(content={
                'message': f'{self.key} not in settings'
            })

    async def __call__(self):
        try:
            result = json_compatible(self.value)
        except (ComponentLookupError, TypeError):
            result = self.value
        return {
            'value': result
        }


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.ReadConfiguration', name='@registry',
    summary='Read container registry settings',
    responses={
        "200": {
            "description": "Successfully registered interface",
            "type": "object",
            "schema": {
                "properties": {
                    "value": {
                        "type": "object"
                    }
                }
            }
        }
    })
async def get_registry(context, request):
    result = {}
    for key in request.container_settings.keys():
        try:
            value = json_compatible(request.container_settings[key])
        except (ComponentLookupError, TypeError):
            value = request.container_settings[key]
        result[key] = value
    return {
        'value': result
    }


@configure.service(
    context=IContainer, method='POST',
    permission='guillotina.RegisterConfigurations', name='@registry',
    summary='Register a new interface to for registry settings',
    parameters=[{
        "name": "body",
        "in": "body",
        "type": "object",
        "schema": {
            "properties": {
                "interface": {
                    "type": "string",
                    "required": True
                },
                "initial_values": {
                    "type": "object",
                    "required": False
                }
            }
        }
    }],
    responses={
        "200": {
            "description": "Successfully registered interface"
        }
    })
class Register(Service):
    """Register an Interface on the Registry."""

    async def __call__(self):
        """ data input : { 'interface': 'INTERFACE' }"""
        if not hasattr(self.request, 'container_settings'):
            return ErrorResponse(
                'BadRequest',
                _("Not in a container request"),
                status=412)

        data = await self.request.json()
        interface = data.get('interface', None)
        initial_values = data.get('initial_values', {})
        if interface is None:
            return ErrorResponse(
                'InvalidRequest',
                'Non existent Interface',
                status=412)

        registry = self.request.container_settings
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

        return Response(status=201)


@configure.service(
    context=IContainer, method='PATCH',
    permission='guillotina.WriteConfiguration', name='@registry/{dotted_name}',
    summary='Update registry setting',
    parameters={
        "name": "body",
        "in": "body",
        "type": "object",
        "schema": {
            "properties": {
                "value": {
                    "type": "any",
                    'required': True
                }
            }
        }
    },
    responses={
        "200": {
            "description": "Successfully wrote configuration"
        }
    })
class Write(Service):
    key = _marker
    value = None

    async def prepare(self):
        self.key = self.request.matchdict['dotted_name']
        self.value = self.request.container_settings.get(self.key)

    async def __call__(self):
        if self.key is _marker:
            # No option to write the root of registry
            return ErrorResponse('InvalidRequest', 'Needs the registry key', status=412)

        data = await self.request.json()
        if 'value' in data:
            value = data['value']
        else:
            value = data

        assert '.' in self.key, 'Registry key must be dotted.iface.name.fieldname'  # noqa
        iface, name = self.key.rsplit('.', 1)
        iface = resolve_dotted_name(iface)

        assert iface is not None, 'Must provide valid registry interface'  # noqa
        try:
            field = iface[name]
        except KeyError:
            return ErrorResponse(
                'DeserializationError',
                'Invalid field name {}'.format(str(name)),
                status=412)

        try:
            new_value = get_adapter((field), IJSONToValue, args=[value, self.context])
        except ComponentLookupError:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(str(self.field)),
                status=412)

        try:
            self.request.container_settings[self.key] = new_value
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                exc=e,
                status=412)

        return Response(status=204)
