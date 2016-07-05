# -*- coding: utf-8 -*-
from plone.server import utils
from plone.server.exceptions import RequestNotFound
from plone.server.catalog.interfaces import ICatalogUtility
from plone.uuid.interfaces import IUUID
from zope.component import getUtility
from zope.component import queryUtility

import asyncio
import logging
import transaction


logger = logging.getLogger('plone.server')


class CommitHook(object):

    def __init__(self):
        self.remove = []
        self.index = {}

    def __call__(self, trns):
        if not trns:
            return
        # Commits are run in sync thread so there is no asyncloop
        loop = asyncio.new_event_loop()
        search = getUtility(ICatalogUtility)
        asyncio.run_coroutine_threadsafe(search.remove(self.remove), loop)
        asyncio.run_coroutine_threadsafe(search.index(self.index), loop)

        self.index = {}
        self.remove = []


def get_hook():

    search = queryUtility(ICatalogUtility)
    if not search:
        return  # no search configured

    try:
        trns = utils.tm(utils.get_current_request()).get()
    except RequestNotFound:
        trns = transaction.get()
    hook = None
    for _hook in trns._after_commit:
        if isinstance(_hook[0], CommitHook):
            hook = _hook[0]
            break
    if hook is None:
        hook = CommitHook()
        trns.addAfterCommitHook(hook)
    return hook


def remove_object(obj, event):
    hook = get_hook()
    if hook is None:
        return
    uid = IUUID(obj, None)
    if uid is None:
        return
    hook.remove.append(uid)
    if uid in hook.index:
        del hook.index[uid]


def add_object(obj, event):
    hook = get_hook()
    if hook is None:
        return
    uid = IUUID(obj, None)
    if uid is None:
        return
    search = queryUtility(ICatalogUtility)
    hook.index[uid] = search.get_data(obj)
