# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server.api.service import Service
from plone.server.browser import get_physical_path
from zope.component import getMultiAdapter


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class DefaultPOST(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()


class DefaultPUT(Service):
    pass


class DefaultPATCH(Service):
    pass


class SharingPOST(Service):
    pass


class DefaultDELETE(Service):
    pass
