from guillotina import configure
from guillotina.browser import Response
from guillotina.component import get_multi_adapter
from guillotina.component import get_utilities_for
from guillotina.component import query_adapter
from guillotina.content import get_cached_factory
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IResource
from guillotina.interfaces import ISchemaSerializeToJson
from guillotina.utils import resolve_dotted_name


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
    data = await request.json()
    behavior = data.get('behavior', None)
    try:
        behavior_class = resolve_dotted_name(behavior)
    except ModuleNotFoundError:
        behavior_class = None
    if behavior_class is None:
        return Response(response={}, status=404)
    factory = get_cached_factory(context.type_name)
    if behavior_class in factory.behaviors:
        return Response(response={}, status=201)
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
    data = await request.json()
    behavior = data.get('behavior', None)
    factory = get_cached_factory(context.type_name)
    behavior_class = resolve_dotted_name(behavior)
    if behavior_class is not None:
        if behavior_class in factory.behaviors:
            return Response(response={}, status=201)
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

    factory = get_cached_factory(context.type_name)

    for name, utility in get_utilities_for(IBehavior):
        serialize = False
        if name not in result['dynamic'] and name not in result['static']:
            adaptable = query_adapter(
                context, utility.interface,
                name='', default=None)
            if adaptable:
                result['available'].append(name)
                serialize = True
                schema_serializer = get_multi_adapter(
                    (utility.interface, request),
                    ISchemaSerializeToJson)
                result[name] = await schema_serializer()
        else:
            serialize = True
        if serialize:
            schema_serializer = get_multi_adapter(
                (utility.interface, request), ISchemaSerializeToJson)
            result[name] = await schema_serializer()
    return result
