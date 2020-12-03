from guillotina import configure
from guillotina.catalog.utils import parse_query
from guillotina.interfaces import IResource
from guillotina.utils import find_container
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
import itertools
from collections import Counter


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.AccessContent",
    name="@suggestion",
    summary="Make suggestion request",
    responses={
        "200": {
            "description": "Search results",
            "type": "object",
            "schema": {"$ref": "#/definitions/SearchResults"},
        }
    },
)
async def suggestion_get(context, request):
    query = request.query.copy()
    search = query_utility(ICatalogUtility)
    if search is None:
        return {}

    fields = request.query.get("_metadata", "").split(",")
    result = await search.query_aggregation(context, query)
    if "member" in result:
        aggregation = []
        for field in fields:
            aggregation.append([])

        for items in result["member"]:
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
