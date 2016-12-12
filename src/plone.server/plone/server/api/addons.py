# -*- coding: utf-8 -*-
from plone.server import _
from plone.server import app_settings
from plone.server.api.service import Service
from plone.server.browser import ErrorResponse
from plone.server.registry import IAddons


class Install(Service):
    async def __call__(self):
        data = await self.request.json()
        id_to_install = data.get('id', None)
        if id_to_install not in app_settings['available_addons']:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"))

        registry = self.request.site_settings
        config = registry.for_interface(IAddons)

        if id_to_install in config.enabled:
            return ErrorResponse(
                'Duplicate',
                _("Addon already installed"))
        handler = app_settings['available_addons'][id_to_install]['handler']
        handler.install(self.request)
        config.enabled |= {id_to_install}
        return await getAddons(self.context, self.request)()


class Uninstall(Service):
    async def __call__(self):
        data = await self.request.json()
        id_to_install = data.get('id', None)
        if id_to_install not in app_settings['available_addons']:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"))

        registry = self.request.site_settings
        config = registry.for_interface(IAddons)

        if id_to_install not in config.enabled:
            return ErrorResponse(
                'Duplicate',
                _("Addon not installed"))

        handler = app_settings['available_addons'][id_to_install]['handler']
        handler.uninstall(self.request)
        config.enabled -= {id_to_install}


class getAddons(Service):
    async def __call__(self):
        result = {
            'available': [],
            'installed': []
        }
        for key, addon in app_settings['available_addons'].items():
            result['available'].append({
                'id': key,
                'title': addon['title']
            })

        registry = self.request.site_settings
        config = registry.for_interface(IAddons)

        for installed in config.enabled:
            result['installed'].append(installed)
        return result
