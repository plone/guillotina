from guillotina import configure
from guillotina._cache import FACTORY_CACHE
from guillotina.component import get_utilities_for
from guillotina.directives import index
from guillotina.directives import merged_tagged_value_dict
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IContainer


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.SearchContent",
    name="@metadata",
    summary="Get available Indexes",
    responses={
        "200": {
            "description": "Result results on indices",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "@id": {"type": "string"},
                            "types": {"type": "object"},
                            "behaviors": {"type": "object"},
                        },
                    }
                }
            },
        }
    },
)
async def get_all_indices(context, request):
    base_url = IAbsoluteURL(context, request)()
    result = {"@id": base_url, "types": {}, "behaviors": {}}
    for type_name, type_schema in FACTORY_CACHE.items():
        indices = merged_tagged_value_dict(type_schema.schema, index.key)
        result["types"][type_name] = {key: value["type"] for key, value in indices.items()}  # noqa

    for behavior, utility in get_utilities_for(IBehavior):
        indices = merged_tagged_value_dict(utility.interface, index.key)
        result["behaviors"][behavior] = {key: value["type"] for key, value in indices.items()}  # noqa
    return result
