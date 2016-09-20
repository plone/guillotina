# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import Service
from plone.server.browser import get_physical_path
from plone.server.browser import Response
from plone.server.browser import ErrorResponse
from zope.component import getMultiAdapter
from plone.dexterity.utils import createContent
from aiohttp.web_exceptions import HTTPUnauthorized, HTTPConflict
from plone.server import AVAILABLE_ADDONS
from plone.server import _
from plone.server.registry import IAddons


class Install(Service):
    async def __call__(self):
        data = await self.request.json()
        id_to_install = data.get('id', None)
        if id_to_install not in AVAILABLE_ADDONS:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"))

        registry = self.request.site_settings
        config = registry.forInterface(IAddons)

        if id_to_install in config.enabled:
            return ErrorResponse(
                'Duplicate',
                _("Addon already installed"))
        handler = AVAILABLE_ADDONS[id_to_install]['handler']
        handler.install(self.request)
        config.enabled.append(id_to_install)


class Uninstall(Service):
    async def __call__(self):
        data = await self.request.json()
        id_to_install = data.get('id', None)
        if id_to_install not in AVAILABLE_ADDONS:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"))

        registry = self.request.site_settings
        config = registry.forInterface(IAddons)

        if id_to_install not in config.enabled:
            return ErrorResponse(
                'Duplicate',
                _("Addon not installed"))

        handler = AVAILABLE_ADDONS[id_to_install]['handler']
        handler.uninstall(self.request)
        config.enabled.remove(id_to_install)


class getAddons(Service):
    async def __call__(self):
        result = {
            'items': []
        }
        for key, addon in AVAILABLE_ADDONS.items():
            result['items'].append({
                'id': key,
                'title': addon['title']
            })
