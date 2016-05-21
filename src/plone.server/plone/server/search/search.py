# -*- coding: utf-8 -*-
from plone.server.api.service import Service
from plone.server.search.interfaces import ISearchUtility
from plone.server.utils import get_content_path
from zope.component import queryUtility
from zope.interface import implementer

import json


class SearchGET(Service):
    async def __call__(self):
        q = self.request.GET.get('q')
        utility = queryUtility(ISearchUtility)
        if not q or utility is None:
            return {
                'items_count': 0,
                'member': []
            }

        return json.dumps(await utility.search(q))


@implementer(ISearchUtility)
class DefaultSearchUtility(object):

    def __init__(self, settings):
        self.settings = settings

    async def search(self, query):
        pass

    async def index(self, datas):
        """
        {uid: <dict>}
        """
        pass

    async def remove(self, uids):
        """
        list of UIDs to remove from index
        """
        pass

    def get_data(self, content):
        return {
            'title': content.title,
            'description': content.description,
            'portal_type': content.portal_type,
            'path': get_content_path(content)
        }
