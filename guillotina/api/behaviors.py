# -*- encoding: utf-8 -*-
from guillotina import configure
from guillotina.browser import Response
from guillotina.component import getMultiAdapter
from guillotina.component import getUtilitiesFor
from guillotina.component import queryAdapter
from guillotina.content import get_cached_factory
from guillotina.db.utils import lock_object
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IResource
from guillotina.interfaces import ISchemaSerializeToJson


@configure.service(
    context=IResource, method='PATCH',
    permission='guillotina.ModifyContent', name='@behaviors',
    summary="Add behavior to resource",
    parameters=[{
        "name": "body",
        "in": "body",
        "schema": {
            "$ref": "#/definitions/Behavior"
        }
    }],
    responses={
        "200": {
            "description": "Successfully added behavior"
        },
        "201": {
            "description": "Behavior already assigned here"
        },
    })
async def default_patch(context, request):
    await lock_object(context)
    data = await request.json()
    behavior = data.get('behavior', None)
    if behavior in context.__behaviors__:
        return Response(response={}, status=201)
    context.add_behavior(behavior)
    return {}


@configure.service(
    context=IResource, method='DELETE',
    permission='guillotina.ModifyContent', name='@behaviors',
    summary="Remove behavior from resource",
    parameters=[{
        "name": "body",
        "in": "body",
        "schema": {
            "$ref": "#/definitions/Behavior"
        }
    }],
    responses={
        "200": {
            "description": "Successfully removed behavior"
        },
        "201": {
            "description": "Behavior not assigned here"
        },
    })
async def default_delete(context, request):
    await lock_object(context)
    data = await request.json()
    behavior = data.get('behavior', None)
    if behavior not in context.__behaviors__:
        return Response(response={}, status=201)
    context.remove_behavior(behavior)
    return {}


@configure.service(
    context=IResource, method='GET',
    permission='guillotina.AccessContent', name='@behaviors',
    summary='Get information on behaviors for this resource',
    responses={
        "200": {
            "description": "A listing of behaviors for content",
            "schema": {
                "$ref": "#/definitions/BehaviorsResponse"
            }
        }
    })
async def default_get(context, request):
    """We show the available schemas."""
    result = {}
    factory = get_cached_factory(context.type_name)
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
