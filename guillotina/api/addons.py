# -*- coding: utf-8 -*-
from guillotina import app_settings
from guillotina import configure
from guillotina.browser import ErrorResponse
from guillotina.interfaces import ISite
from guillotina.registry import IAddons
from zope.i18nmessageid import MessageFactory

import asyncio


_ = MessageFactory('guillotina')


@configure.service(context=ISite, name='@addons', method='POST',
                   permission='guillotina.ManageAddons')
async def install(context, request):
    data = await request.json()
    id_to_install = data.get('id', None)
    if id_to_install not in app_settings['available_addons']:
        return ErrorResponse(
            'RequiredParam',
            _("Property 'id' is required to be valid"))

    registry = request.site_settings
    config = registry.for_interface(IAddons)

    if id_to_install in config.enabled:
        return ErrorResponse(
            'Duplicate',
            _("Addon already installed"))
    handler = app_settings['available_addons'][id_to_install]['handler']
    if asyncio.iscoroutinefunction(handler.install):
        await handler.install(context, request)
    else:
        handler.install(context, request)
    config.enabled |= {id_to_install}
    return await get_addons(context, request)()


@configure.service(context=ISite, name='@addons', method='DELETE',
                   permission='guillotina.ManageAddons')
async def uninstall(context, request):
    data = await request.json()
    id_to_install = data.get('id', None)
    if id_to_install not in app_settings['available_addons']:
        return ErrorResponse(
            'RequiredParam',
            _("Property 'id' is required to be valid"))

    registry = request.site_settings
    config = registry.for_interface(IAddons)

    if id_to_install not in config.enabled:
        return ErrorResponse(
            'Duplicate',
            _("Addon not installed"))

    handler = app_settings['available_addons'][id_to_install]['handler']
    if asyncio.iscoroutinefunction(handler.install):
        await handler.uninstall(context, request)
    else:
        handler.uninstall(context, request)
    config.enabled -= {id_to_install}


@configure.service(context=ISite, name='@addons', method='GET',
                   permission='guillotina.ManageAddons')
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

    registry = request.site_settings
    config = registry.for_interface(IAddons)

    for installed in config.enabled:
        result['installed'].append(installed)
    return result
