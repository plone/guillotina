from guillotina import configure
from guillotina import error_reasons
from guillotina._settings import app_settings
from guillotina.browser import ErrorResponse
from guillotina.i18n import MessageFactory
from guillotina.interfaces import IAddons
from guillotina.interfaces import IContainer
from guillotina.utils import apply_coroutine


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
    data = await request.json()
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
    handler = app_settings['available_addons'][id_to_install]['handler']
    await apply_coroutine(handler.install, context, request)
    config['enabled'] |= {id_to_install}
    return await get_addons(context, request)


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
    data = await request.json()
    id_to_install = data.get('id', None)
    if id_to_install not in app_settings['available_addons']:
        return ErrorResponse(
            'RequiredParam',
            _("Property 'id' is required to be valid"),
            status=412, reason=error_reasons.INVALID_ID)

    registry = request.container_settings
    config = registry.for_interface(IAddons)

    if id_to_install not in config['enabled']:
        return ErrorResponse(
            'Duplicate',
            _("Addon not installed"),
            status=412, reason=error_reasons.NOT_INSTALLED)

    handler = app_settings['available_addons'][id_to_install]['handler']
    await apply_coroutine(handler.uninstall, context, request)
    config['enabled'] -= {id_to_install}


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
            'title': addon['title']
        })

    registry = request.container_settings
    config = registry.for_interface(IAddons)

    for installed in config['enabled']:
        result['installed'].append(installed)
    return result
