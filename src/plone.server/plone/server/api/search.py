# -*- coding: utf-8 -*-
from plone.server.api.service import Service
from plone.server.catalog.interfaces import ICatalogUtility
from zope.component import queryUtility


class SearchGET(Service):
    async def __call__(self):
        q = self.request.GET.get('q')
        utility = queryUtility(ICatalogUtility)
        if utility is None:
            return {
                'items_count': 0,
                'member': []
            }

        return await utility.search(q, self.request._site_id)


class SearchPOST(Service):
    async def __call__(self):
        q = await self.request.json()
        utility = queryUtility(ICatalogUtility)
        if utility is None:
            return {
                'items_count': 0,
                'member': []
            }

        return await utility.search(q, self.request._site_id)


class ReindexPOST(Service):
    """ Creates index / catalog and reindex all content
    """
    async def __call__(self):
        utility = queryUtility(ICatalogUtility)
        await utility.reindexAllContent(self.request.site)
        return {}