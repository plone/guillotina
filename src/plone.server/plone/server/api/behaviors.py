# -*- encoding: utf-8 -*-
from plone.behavior.interfaces import IBehavior
from plone.server.api.service import Service
from plone.server.content import getCachedFactory
from plone.server.json.interfaces import ISchemaSerializeToJson
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.component import queryAdapter
from zope.interface import Interface


class DefaultPATCH(Service):
    async def __call__(self):
        """We add a behavior.

        We expect on the body to be :
        {
            'behavior': 'INTERFACE.TO.BEHAVIOR.SCHEMA'
        }
        """
        data = await self.request.json()
        behavior = data.get('behavior', None)
        self.context.add_behavior(behavior)
        return {}


class DefaultDELETE(Service):
    async def __call__(self):
        """We add a behavior.

        We expect on the body to be :
        {
            'behavior': 'INTERFACE.TO.BEHAVIOR.SCHEMA'
        }
        """
        data = await self.request.json()
        behavior = data.get('behavior', None)
        self.context.remove_behavior(behavior)
        return {}


class DefaultGET(Service):
    async def __call__(self):
        """We show the available schemas."""
        result = {}
        factory = getCachedFactory(self.context.portal_type)
        result['static'] = []
        for schema in factory.behaviors or ():
            result['static'].append(schema.__identifier__)
        result['dynamic'] = self.context.__behaviors__
        result['available'] = []

        for iface, utility in getUtilitiesFor(IBehavior):
            serialize = False
            if isinstance(iface, str):
                name = iface
            else:
                name = iface.__identifier__
            if name not in result['dynamic'] and name not in result['static']:
                adaptable = queryAdapter(
                    self.context, utility.interface,
                    name='', default=None)
                if adaptable:
                    result['available'].append(name)
                    serialize = True
                    schema_serializer = getMultiAdapter(
                        (utility.interface, self.request),
                        ISchemaSerializeToJson)
                    result[name] = schema_serializer()
            else:
                serialize = True
            if serialize:
                schema_serializer = getMultiAdapter(
                    (utility.interface, self.request), ISchemaSerializeToJson)
                result[name] = schema_serializer()
        return result
