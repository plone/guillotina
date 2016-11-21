# -*- coding: utf-8 -*-
from plone.server.catalog.interfaces import ICatalogUtility
from plone.server.transactions import get_current_request
from plone.server.transactions import RequestNotFound
from plone.server.transactions import tm
from zope.component import getUtility
from zope.component import queryUtility

import asyncio
import logging
import transaction


logger = logging.getLogger('plone.server')


class CommitHook(object):

    def __init__(self, site_id, loop):
        self.remove = []
        self.index = {}
        self.site_id = site_id
        self.loop = loop

    async def __call__(self, trns):
        if not trns:
            return
        # Commits are run in sync thread so there is no asyncloop
        search = getUtility(ICatalogUtility)
        await search.remove(self.remove, self.site_id)
        await search.index(self.index, self.site_id)

        self.index = {}
        self.remove = []


def get_hook():

    search = queryUtility(ICatalogUtility)
    if not search:
        return  # no search configured

    request = get_current_request()
    try:
        trns = tm(request).get()
    except RequestNotFound:
        trns = transaction.get()
    hook = None
    for _hook in trns._after_commit:
        if isinstance(_hook[0], CommitHook):
            hook = _hook[0]
            break
    if hook is None:
        loop = asyncio.get_event_loop()
        hook = CommitHook(request._site_id, loop)
        trns.addAfterCommitHook(hook)
    return hook


def remove_object(obj, event):
    hook = get_hook()
    if hook is None:
        return
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    hook.remove.append(uid)
    if uid in hook.index:
        del hook.index[uid]


def add_object(obj, event):
    hook = get_hook()
    if hook is None:
        return
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    search = queryUtility(ICatalogUtility)
    if search is not None:
        hook.index[uid] = search.get_data(obj)


async def add_index(obj, event):
    search = queryUtility(ICatalogUtility)
    if search is not None:
        await search.create_index(obj.id)


async def remove_index(obj, event):
    search = queryUtility(ICatalogUtility)
    if search is not None:
        await search.remove_index(obj.id)
