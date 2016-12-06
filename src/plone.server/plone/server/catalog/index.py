# -*- coding: utf-8 -*-
from plone.server.interfaces import ICatalogUtility
from plone.server.interfaces import ISite
from plone.server.transactions import get_current_request
from plone.server.transactions import RequestNotFound
from plone.server.transactions import tm
from zope.component import queryUtility

import logging
import transaction


logger = logging.getLogger('plone.server')


class CommitHook(object):

    def __init__(self, site, request):
        self.remove = []
        self.index = {}
        self.site = site
        self.request = request

    async def __call__(self, trns):
        if not trns:
            return
        # Commits are run in sync thread so there is no asyncloop
        search = queryUtility(ICatalogUtility)
        if search:
            await search.remove(self.site, self.remove)
            await search.index(self.site, self.index)

        self.index = {}
        self.remove = []


def get_hook():

    request = get_current_request()
    try:
        site = request.site
        search = queryUtility(ICatalogUtility)
    except (AttributeError, KeyError):
        return

    if not search:
        return  # no search configured

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
        hook = CommitHook(site, request)
        trns.addAfterCommitHook(hook)
    return hook


def remove_object(obj, event):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    portal_type = getattr(obj, 'portal_type', None)
    if portal_type is None or ISite.providedBy(obj):
        return

    hook = get_hook()
    if hook is None:
        return
    hook.remove.append((uid, portal_type))
    if uid in hook.index:
        del hook.index[uid]


def add_object(obj, event):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    portal_type = getattr(obj, 'portal_type', None)
    if portal_type is None or ISite.providedBy(obj):
        return

    hook = get_hook()
    if hook is None:
        return
    search = queryUtility(ICatalogUtility)
    if search:
        hook.index[uid] = search.get_data(obj)


async def initialize_catalog(site, event):
    search = queryUtility(ICatalogUtility)
    if search:
        await search.initialize_catalog(site)


async def remove_catalog(site, event):
    search = queryUtility(ICatalogUtility)
    if search:
        await search.remove_catalog(site)
