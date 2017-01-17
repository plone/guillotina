# -*- coding: utf-8 -*-
from plone.server.configure import service
from plone.server.api.service import Service
from plone.server.interfaces import ICatalogUtility
from plone.server.interfaces import IResource
from zope.component import queryUtility
from plone.server.utils import get_content_path
from plone.server.async import IQueueUtility


@service(context=IResource, method='GET', permission='plone.SearchContent',
         name='@search')
async def search_get(context, request):
    q = request.GET.get('q')
    search = queryUtility(ICatalogUtility)
    if search is None:
        return {
            'items_count': 0,
            'member': []
        }

    return await search.get_by_path(
        site=request.site,
        path=get_content_path(context),
        query=q)


@service(context=IResource, method='POST', permission='plone.RawSearchContent',
         name='@search')
async def search_post(context, request):
    q = await request.json()
    search = queryUtility(ICatalogUtility)
    if search is None:
        return {
            'items_count': 0,
            'member': []
        }

    return await search.query(context, q)


@service(context=IResource, method='POST', permission='plone.ReindexContent',
         name='@catalog-reindex')
class CatalogReindex(Service):

    async def __call__(self):
        search = queryUtility(ICatalogUtility)
        await search.reindex_all_content(self.context)
        return {}


@service(context=IResource, method='POST', permission='plone.ReindexContent',
         name='@async-catalog-reindex')
async def async_catalog_reindex(context, request):
    util = queryUtility(IQueueUtility)
    import pdb; pdb.set_trace()
    await util.add(CatalogReindex(context, request))
    return {}


@service(context=IResource, method='POST', permission='plone.ManageCatalog',
         name='@catalog')
async def catalog_post(context, request):
    search = queryUtility(ICatalogUtility)
    await search.initialize_catalog(context)
    return {}


@service(context=IResource, method='DELETE', permission='plone.ManageCatalog',
         name='@catalog')
async def catalog_delete(context, request):
    search = queryUtility(ICatalogUtility)
    await search.remove_catalog(context)
    return {}
