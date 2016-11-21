# -*- coding: utf-8 -*-
from plone.server import app_settings
from plone.server.api.service import Service
from plone.server.json.interfaces import IResourceSerializeToJson
from zope.component import getMultiAdapter

import logging


logger = logging.getLogger(__name__)


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        return serializer()


class GetAPIDefinition(Service):
    async def __call__(self):
        return app_settings['api_definition']
