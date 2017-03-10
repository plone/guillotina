# -*- encoding: utf-8 -*-
from guillotina import configure
from guillotina.component import getMultiAdapter
from guillotina.component import getUtilitiesFor
from guillotina.component import queryAdapter
from guillotina.content import get_cached_factory
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IResource
from guillotina.interfaces import ISchemaSerializeToJson


@configure.service(context=IResource, method='PATCH', permission='guillotina.ModifyContent',
                   name='@behaviors')
async def default_patch(context, request):
    """We add a behavior.

    We expect on the body to be :
    {
        'behavior': 'INTERFACE.TO.BEHAVIOR.SCHEMA'
    }
    """
    data = await request.json()
    behavior = data.get('behavior', None)
    context.add_behavior(behavior)
    return {}


@configure.service(context=IResource, method='DELETE', permission='guillotina.ModifyContent',
                   name='@behaviors')
async def default_delete(context, request):
    """We add a behavior.

    We expect on the body to be :
    {
        'behavior': 'INTERFACE.TO.BEHAVIOR.SCHEMA'
    }
    """
    data = await request.json()
    behavior = data.get('behavior', None)
    context.remove_behavior(behavior)
    return {}


@configure.service(
    context=IResource, method='GET', permission='guillotina.AccessContent',
    name='@behaviors',
    description='Get information on behaviors for this resource')
async def default_get(context, request):
    """We show the available schemas."""
    result = {}
    factory = get_cached_factory(context.portal_type)
    result['static'] = []
    for schema in factory.behaviors or ():
        result['static'].append(schema.__identifier__)

    # convert to list, could be frozenset
    result['dynamic'] = [b for b in context.__behaviors__]

    result['available'] = []

    for iface, utility in getUtilitiesFor(IBehavior):
        serialize = False
        if isinstance(iface, str):
            name = iface
        else:
            name = iface.__identifier__
        if name not in result['dynamic'] and name not in result['static']:
            adaptable = queryAdapter(
                context, utility.interface,
                name='', default=None)
            if adaptable:
                result['available'].append(name)
                serialize = True
                schema_serializer = getMultiAdapter(
                    (utility.interface, request),
                    ISchemaSerializeToJson)
                result[name] = await schema_serializer()
        else:
            serialize = True
        if serialize:
            schema_serializer = getMultiAdapter(
                (utility.interface, request), ISchemaSerializeToJson)
            result[name] = await schema_serializer()
    return result
