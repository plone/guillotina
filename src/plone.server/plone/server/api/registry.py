# -*- coding: utf-8 -*-
from plone.jsonserializer.exceptions import DeserializationError
from plone.jsonserializer.interfaces import IFieldDeserializer
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.server import _
from plone.server.api.service import Service
from plone.server.api.service import TraversableService
from plone.server.browser import ErrorResponse
from plone.server.browser import Response
from plone.server.interfaces import IRegistry
from plone.server.utils import import_class
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.interface.interfaces import ComponentLookupError
from zope.schema import getFields


class Read(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.value = [self.request.site_settings[traverse[0]]]
        else:
            self.value = None
        return self

    async def __call__(self):
        if not hasattr(self, 'value'):
            # Root of registry
            self.value = self.request.site_settings
        if IRegistry.providedBy(self.value):
            result = {}
            for x in self.value.records:
                try:
                    serializer = getMultiAdapter(
                        (self.value[x], self.request),
                        ISerializeToJson)
                    value = serializer()
                except ComponentLookupError:
                    value = self.value[x]
                result[x] = value
        else:
            try:
                serializer = getMultiAdapter(
                    (self.value, self.request),
                    ISerializeToJson)

                result = serializer()
            except ComponentLookupError:
                result = self.value
        return result


class Register(Service):
    """Register an Interface on the Registry"""

    async def __call__(self):
        """ data input : { 'interface': 'INTERFACE' }"""
        if not hasattr(self.request, 'site_settings'):
            return ErrorResponse(
                'BadRequest',
                _("Not in a site request"))

        data = await self.request.json()
        interface = data.get('interface', None)
        initial_values = data.get('initial_values', {})
        if interface is None:
            return ErrorResponse(
                'InvalidRequest',
                'Non existent Interface')

        registry = self.request.site_settings
        iObject = import_class(interface)
        registry.registerInterface(iObject)
        config = registry.forInterface(iObject)

        # Initialize values
        # If its defined on the zope.schema default will not be overwritten
        #  you will need to PATCH
        for key, field in getFields(iObject).items():
            if key in initial_values and not getattr(config, key, False):
                # We don't have a value
                setattr(config, key, initial_values[key])

        return Response(response={}, status=201)


class Write(TraversableService):

    def publishTraverse(self, traverse):
        if len(traverse) == 1 and traverse[0] in self.request.site_settings:
            # we want have the key of the registry
            self.record = self.request.site_settings._data[traverse[0]]
        else:
            self.record = None
        return self

    async def __call__(self):
        if getattr(self, 'record', None) is None:
            # No option to write the root of registry
            return ErrorResponse(
                'InvalidRequest',
                'Needs the registry field')
        data = await self.request.json()
        if 'value' in data:
            value = data['value']
        else:
            value = data

        deserializer = queryMultiAdapter(
            (self.record.field, self.request.site_settings, self.request),
            IFieldDeserializer)

        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(str(self.record)),
                status=501)

        try:
            self.record.value = deserializer(value)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        return Response(response={}, status=204)
