# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.api.search import AsyncCatalogReindex
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectRemovedEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IObjectPermissionsModifiedEvent
from guillotina.interfaces import IResource
from guillotina.interfaces import ISite
from guillotina.utils import get_current_request
from guillotina.transactions import tm
from guillotina.utils import get_content_path
from zope.component import queryUtility


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

    trns = tm(request).get()
    hook = None
    for _hook in trns._after_commit:
        if isinstance(_hook[0], CommitHook):
            hook = _hook[0]
            break
    if hook is None:
        hook = CommitHook(site, request)
        trns.add_after_commit_hook(hook)
    return hook


@configure.subscriber(for_=(IResource, IObjectPermissionsModifiedEvent))
async def security_changed(obj, event):
    # We need to reindex the objects below
    request = get_current_request()
    await AsyncCatalogReindex(obj, request, security=True)()


@configure.subscriber(for_=(IResource, IObjectRemovedEvent))
def remove_object(obj, event):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    portal_type = getattr(obj, 'portal_type', None)
    if portal_type is None or ISite.providedBy(obj):
        return

    content_path = get_content_path(obj)

    hook = get_hook()
    if hook is None:
        return
    hook.remove.append((uid, portal_type, content_path))
    if uid in hook.index:
        del hook.index[uid]


@configure.subscriber(for_=(IResource, IObjectAddedEvent))
@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
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


@configure.subscriber(for_=(ISite, IObjectAddedEvent))
async def initialize_catalog(site, event):
    search = queryUtility(ICatalogUtility)
    if search:
        await search.initialize_catalog(site)


@configure.subscriber(for_=(ISite, IObjectRemovedEvent))
async def remove_catalog(site, event):
    search = queryUtility(ICatalogUtility)
    if search:
        await search.remove_catalog(site)
