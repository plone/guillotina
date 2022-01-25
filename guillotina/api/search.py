from guillotina import configure
from guillotina.api.service import Service
from guillotina.catalog.utils import reindex_in_future
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.response import HTTPServiceUnavailable

import logging


logger = logging.getLogger("guillotina")

QUERY_PARAMETERS = [
    {
        "in": "query",
        "required": False,
        "name": "term",
        "description": "Generic search term support. See modifier list below for usage.",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_from",
        "description": "Start with search result _from.",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_size",
        "description": "Size of result set. Max to 50 (app_settings.catalog_max_results).",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_sort_asc",
        "description": "Sort ascending by index _sort_asc.",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_sort_des",
        "description": "Sort descending by index _sort_des.",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_metadata",
        "description": "List of metadata fields to include",
        "schema": {"type": "string"},
    },
    {
        "in": "query",
        "required": False,
        "name": "_metadata_not",
        "description": "List of metadata fields to exclude",
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
    search = query_utility(ICatalogUtility)
    if search is None:
        raise HTTPServiceUnavailable()

    return await search.search(context, dict(request.query))


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
    search = query_utility(ICatalogUtility)
    if search is None:
        raise HTTPServiceUnavailable()

    return await search.search_raw(context, q)


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
        if search is None:
            raise HTTPServiceUnavailable()
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
    if search is None:
        raise HTTPServiceUnavailable()
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
    if search is None:
        raise HTTPServiceUnavailable()
    await search.remove_catalog(context)
    return {}
