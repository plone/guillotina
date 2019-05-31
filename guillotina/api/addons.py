from guillotina import addons
from guillotina import configure
from guillotina import error_reasons
from guillotina._settings import app_settings
from guillotina.i18n import MessageFactory
from guillotina.interfaces import IAddons
from guillotina.interfaces import IContainer
from guillotina.response import ErrorResponse
from guillotina.utils import get_schema_validator
from guillotina.response import HTTPPreconditionFailed


import jsonschema

_ = MessageFactory('guillotina')


@configure.service(
    context=IContainer, method='POST',
    permission='guillotina.ManageAddons', name='@addons',
    summary='Install addon to container',
    parameters=[{
        "name": "body",
        "in": "body",
        "schema": {
            "$ref": "#/definitions/Addon"
        }
    }])
async def install(context, request):
    validator = get_schema_validator('Addon')
    try:
        data = await request.json()
        validator.validate(data)
        id_to_install = data.get('id', None)
        
        if id_to_install not in app_settings['available_addons']:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"),
                status=412, reason=error_reasons.INVALID_ID)

        registry = request.container_settings
        config = registry.for_interface(IAddons)

        if id_to_install in config['enabled']:
            return ErrorResponse(
                'Duplicate',
                _("Addon already installed"),
                status=412, reason=error_reasons.ALREADY_INSTALLED)

        await addons.install(context, id_to_install)
        return await get_addons(context, request)
    except jsonschema.exceptions.ValidationError as e:
        raise HTTPPreconditionFailed(content={
            'reason': 'json schema validation error',
            'message': e.message,
            'validator': e.validator,
            'validator_value': e.validator_value,
            'path': [i for i in e.path],
            'schema_path': [i for i in e.schema_path],
            "schema": app_settings['json_schema_definitions']['Addon']
        })



@configure.service(
    context=IContainer, method='DELETE',
    permission='guillotina.ManageAddons', name='@addons',
    summary='Uninstall an addon from container',
    parameters=[{
        "name": "body",
        "in": "body",
        "schema": {
            "$ref": "#/definitions/Addon"
        }
    }])
async def uninstall(context, request):
    validator = get_schema_validator('Addon')
    try:
        data = await request.json()
        validator.validate(data)
        id_to_uninstall = data.get('id', None)
        return await uninstall_addon(context, request, id_to_uninstall)
    except jsonschema.exceptions.ValidationError as e:
        raise HTTPPreconditionFailed(content={
            'reason': 'json schema validation error',
            'message': e.message,
            'validator': e.validator,
            'validator_value': e.validator_value,
            'path': [i for i in e.path],
            'schema_path': [i for i in e.schema_path],
            "schema": app_settings['json_schema_definitions']['Addon']
        })


@configure.service(
    context=IContainer, method='DELETE',
    permission='guillotina.ManageAddons', name='@addons/{addon}',
    summary='Uninstall an addon from container',
    parameters=[{
        "name": "addon",
        "in": "path",
    }])
async def uninstall_path(context, request):
    id_to_uninstall = request.matchdict['addon']
    return await uninstall_addon(context, request, id_to_uninstall)


async def uninstall_addon(context, request, id_to_uninstall):
    if id_to_uninstall not in app_settings['available_addons']:
        return ErrorResponse(
            'RequiredParam',
            _("Property 'id' is required to be valid"),
            status=412, reason=error_reasons.INVALID_ID)

    registry = request.container_settings
    config = registry.for_interface(IAddons)

    if id_to_uninstall not in config['enabled']:
        return ErrorResponse(
            'Duplicate',
            _("Addon not installed"),
            status=412, reason=error_reasons.NOT_INSTALLED)

    await addons.uninstall(context, id_to_uninstall)


@configure.service(
    context=IContainer, method='GET',
    permission='guillotina.ManageAddons', name='@addons',
    summary='List available addons',
    responses={
        "200": {
            "description": "Get list of available and installed addons",
            "schema": {
                "$ref": "#/definitions/AddonResponse"
            }
        }
    })
async def get_addons(context, request):
    result = {
        'available': [],
        'installed': []
    }
    for key, addon in app_settings['available_addons'].items():
        result['available'].append({
            'id': key,
            'title': addon['title'],
            'dependencies': addon['dependencies']
        })

    registry = request.container_settings
    config = registry.for_interface(IAddons)

    for installed in config['enabled']:
        result['installed'].append(installed)
    return result
