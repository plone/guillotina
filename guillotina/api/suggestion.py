from collections import Counter
from guillotina import configure
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.response import HTTPServiceUnavailable


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.AccessContent",
    name="@suggestion",
    summary="Make suggestion request",
    responses={
        "200": {
            "description": "Suggestion results",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"count": {"type": "integer"}, "items": {"type": "array"}},
                    }
                }
            },
        }
    },
)
async def suggestion_get(context, request):
    query = request.query.copy()
    search = query_utility(ICatalogUtility)
    if search is None:
        raise HTTPServiceUnavailable()

    fields = request.query.get("_metadata", "").split(",")
    result = await search.query_aggregation(context, query)
    if "items" in result:
        aggregation = []
        for field in fields:
            aggregation.append([])

        for items in result["items"]:
            for index, item in enumerate(items):
                if isinstance(item, list):
                    aggregation[index].extend(item)
                elif isinstance(item, str):
                    aggregation[index].append(item)

        final_result = {}

        for index, field in enumerate(fields):
            elements = dict(Counter(aggregation[index]))
            final_result[field] = {"items": elements, "total": len(elements)}
        return final_result
    else:
        return {}
