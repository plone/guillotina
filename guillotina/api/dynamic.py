from guillotina import configure
from guillotina.behaviors.dynamic import get_all_fields
from guillotina.interfaces import IResource


@configure.service(
    context=IResource, method='GET',
    name="@dynamic-fields", permission='guillotina.ModifyContent',
    summary="Get a list of available fields")
async def available_dynamic_fields(context, request):
    return get_all_fields(context)
