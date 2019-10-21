from guillotina import configure
from guillotina.api.service import Service
from guillotina.catalog.utils import reindex_in_future
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource

import logging


logger = logging.getLogger("guillotina")

QUERY_PARAMETERS = [
    {
        "in": "query",
        "required": False,
        "name": "term",
        "description": "Generic search term support. See modifier list below for usage",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_from",
        "description": "start from a point in search results",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_size",
        "description": "How large of result set. Max of 50.",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_sort_asc",
        "description": "How ascending field",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_sort_des",
        "description": "How descending field",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_metadata",
        "description": "list of metadata fields to include",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_metadata_not",
        "description": "list of metadata fields to exclude",
        "schema": {"type": "string"},
    },
    {"in": "query", "required": False, "name": "__eq", "schema": {"type": "string"}},
    {"in": "query", "required": False, "name": "__not", "schema": {"type": "string"}},
    {"in": "query", "required": False, "name": "__gt", "schema": {"type": "string"}},
    {"in": "query", "required": False, "name": "__gte", "schema": {"type": "string"}},
    {"in": "query", "required": False, "name": "__lte", "schema": {"type": "string"}},
    {"in": "query", "required": False, "name": "__lt", "schema": {"type": "string"}},
    {"in": "query", "required": False, "name": "__in", "schema": {"type": "string"}},
]


async def _search(context, request, query):
    search = query_utility(ICatalogUtility)
    if search is None:
        return {"items_count": 0, "member": []}

    return await search.query(context, query)


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.SearchContent",
    name="@search",
    validate=True,
    parameters=QUERY_PARAMETERS,
    summary="Make search request",
    responses={
        "200": {
            "description": "Search results",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "$ref": "#/components/schemas/SearchResults"}
                }
            },
        }
    },
)
async def search_get(context, request):
    q = dict(request.url.query)
    return await _search(context, request, q)


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.RawSearchContent",
    name="@search",
    summary="Make a complex search query",
    requestBody={"content": {"application/json": {"schema": {"properties": {}}}}},
    responses={
        "200": {
            "description": "Search results",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "$ref": "#/components/schemas/SearchResults"}
                }
            },
        }
    },
)
async def search_post(context, request):
    q = await request.json()
    return await _search(context, request, q)


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ReindexContent",
    name="@catalog-reindex",
    summary="Reindex entire container content",
    responses={"200": {"description": "Successfully reindexed content"}},
)
class CatalogReindex(Service):
    def __init__(self, context, request, security=False):
        super(CatalogReindex, self).__init__(context, request)
        self._security_reindex = security

    async def __call__(self):
        search = query_utility(ICatalogUtility)
        if search is not None:
            await search.reindex_all_content(self.context, self._security_reindex)
        return {}


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ReindexContent",
    name="@async-catalog-reindex",
    summary="Asynchronously reindex entire container content",
    responses={"200": {"description": "Successfully initiated reindexing"}},
)
class AsyncCatalogReindex(Service):
    def __init__(self, context, request, security=False):
        super(AsyncCatalogReindex, self).__init__(context, request)
        self._security_reindex = security

    async def __call__(self):
        reindex_in_future(self.context, False)
        return {}


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ManageCatalog",
    name="@catalog",
    summary="Initialize catalog",
    responses={"200": {"description": "Successfully initialized catalog"}},
)
async def catalog_post(context, request):
    search = query_utility(ICatalogUtility)
    await search.initialize_catalog(context)
    return {}


@configure.service(
    context=IResource,
    method="DELETE",
    permission="guillotina.ManageCatalog",
    name="@catalog",
    summary="Delete search catalog",
    responses={"200": {"description": "Successfully deleted catalog"}},
)
async def catalog_delete(context, request):
    search = query_utility(ICatalogUtility)
    await search.remove_catalog(context)
    return {}
