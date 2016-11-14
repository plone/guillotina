# -*- coding: utf-8 -*-
from plone.server import _
from plone.server.api.service import Service
from plone.server.api.service import TraversableService
from plone.server.browser import ErrorResponse
from plone.server.browser import Response
from plone.server.interfaces import IRegistry
from plone.server.json.exceptions import DeserializationError
from plone.server.json.interfaces import IJSONToValue
from plone.server.json.interfaces import IValueToJson
from plone.server.utils import import_class
from zope.component import getMultiAdapter
from zope.dottedname.resolve import resolve
from zope.interface.interfaces import ComponentLookupError
from zope.schema import getFields


_marker = object()


class Read(TraversableService):
    key = _marker
    value = None

    def publishTraverse(self, traverse):
        if len(traverse) == 1:
            # we want have the key of the registry
            self.key = traverse[0]
            self.value = self.request.site_settings[self.key]
        return self

    async def __call__(self):
        if self.key is _marker:
            # Root of registry
            self.value = self.request.site_settings
        if IRegistry.providedBy(self.value):
            result = {}
            for x in self.value:
                try:
                    value = IValueToJson(self.value[x])
                except ComponentLookupError:
                    value = self.value[x]
                result[x] = value
        else:
            try:
                result = IValueToJson(self.value)
            except ComponentLookupError:
                result = self.value
        return result


class Register(Service):
    """Register an Interface on the Registry."""

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
    key = _marker
    value = None

    def publishTraverse(self, traverse):
        if len(traverse) == 1 and traverse[0] in self.request.site_settings:
            # we want have the key of the registry
            self.key = traverse[0]
            self.value = self.request.site_settings[self.key]
        return self

    async def __call__(self):
        if self.key is _marker:
            # No option to write the root of registry
            return ErrorResponse('InvalidRequest', 'Needs the registry key')

        data = await self.request.json()
        if 'value' in data:
            value = data['value']
        else:
            value = data

        assert '.' in self.key, 'Registry key must be dotted.iface.name.fieldname'  # noqa
        iface, name = self.key.rsplit('.', 1)
        iface = resolve(iface)
        field = iface[name]

        try:
            new_value = getMultiAdapter((value, field), IJSONToValue)
        except ComponentLookupError:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(str(self.field)),
                status=501)

        try:
            self.request.site_settings[self.key] = new_value
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        return Response(response={}, status=204)
