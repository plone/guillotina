# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server import JSON_API_DEFINITION
from plone.server.api.service import Service
from zope.component import getMultiAdapter

import logging


logger = logging.getLogger(__name__)


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class GetAPIDefinition(Service):
    async def __call__(self):
        return JSON_API_DEFINITION
