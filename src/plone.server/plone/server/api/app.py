# -*- coding: utf-8 -*-
from plone.server.json.interfaces import IResourceSerializeToJson
from plone.server import JSON_API_DEFINITION
from plone.server.api.service import Service
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
        return JSON_API_DEFINITION
