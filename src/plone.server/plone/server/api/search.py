# -*- coding: utf-8 -*-
from plone.server.api.service import Service
from plone.server.interfaces import ICatalogUtility
from zope.component import queryUtility


class SearchGET(Service):
    async def __call__(self):
        q = self.request.GET.get('q')
        search = queryUtility(ICatalogUtility)
        if search is None:
            return {
                'items_count': 0,
                'member': []
            }

        return await search.search(self.context, q)


class SearchPOST(Service):
    async def __call__(self):
        q = await self.request.json()
        search = queryUtility(ICatalogUtility)
        if search is None:
            return {
                'items_count': 0,
                'member': []
            }

        return await search.query(self.context, q)


class ReindexPOST(Service):
    """ Creates index / catalog and reindex all content
    """
    async def __call__(self):
        search = queryUtility(ICatalogUtility)
        await search.reindex_all_content(self.context)
        return {}


class CatalogPOST(Service):
    async def __call__(self):
        search = queryUtility(ICatalogUtility)
        await search.initialize_catalog(self.context)
        return {}


class CatalogDELETE(Service):
    async def __call__(self):
        search = queryUtility(ICatalogUtility)
        await search.remove_catalog(self.context)
        return {}
