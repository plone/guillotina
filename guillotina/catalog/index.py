from guillotina import configure
from guillotina.api.search import AsyncCatalogReindex
from guillotina.component import query_utility
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IContainer
from guillotina.interfaces import IGroupFolder
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IObjectMovedEvent
from guillotina.interfaces import IObjectPermissionsModifiedEvent
from guillotina.interfaces import IObjectRemovedEvent
from guillotina.interfaces import IResource
from guillotina.utils import get_content_path
from guillotina.utils import get_current_request


class IndexFuture(object):

    def __init__(self, container, request):
        self.remove = []
        self.index = {}
        self.update = {}
        self.container = container
        self.request = request

    async def __call__(self):
        if self.request.view_error:
            # there was an error executing this view, we do not want to execute
            return

        # Commits are run in sync thread so there is no asyncloop
        search = query_utility(ICatalogUtility)
        if search:
            if len(self.remove) > 0:
                await search.remove(self.container, self.remove)
            if len(self.index) > 0:
                await search.index(self.container, self.index)
            if len(self.update) > 0:
                await search.update(self.container, self.update)

        self.index = {}
        self.update = {}
        self.remove = []


def get_future():

    request = get_current_request()
    try:
        container = request.container
        search = query_utility(ICatalogUtility)
    except (AttributeError, KeyError):
        return

    if not search:
        return  # no search configured

    fut = request.get_future('indexer')
    if fut is None:
        fut = IndexFuture(container, request)
        request.add_future('indexer', fut)
    return fut


@configure.subscriber(for_=(IResource, IObjectPermissionsModifiedEvent))
async def security_changed(obj, event):
    if IGroupFolder.providedBy(obj):
        # assuming permissions for group are already handled correctly with
        # group:group id principal
        return
    # We need to reindex the objects below
    request = get_current_request()
    request.add_future(
        obj.id, AsyncCatalogReindex(obj, request, security=True)())


@configure.subscriber(for_=(IResource, IObjectMovedEvent))
def moved_object(obj, event):
    request = get_current_request()
    request.add_future(
        obj.id, AsyncCatalogReindex(obj, request, security=True)())


@configure.subscriber(for_=(IResource, IObjectRemovedEvent))
def remove_object(obj, event):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    type_name = getattr(obj, 'type_name', None)
    if type_name is None or IContainer.providedBy(obj):
        return

    content_path = get_content_path(obj)

    fut = get_future()
    if fut is None:
        return

    fut.remove.append((uid, type_name, content_path))
    if uid in fut.index:
        del fut.index[uid]
    if uid in fut.update:
        del fut.update[uid]


@configure.subscriber(for_=(IResource, IObjectAddedEvent))
@configure.subscriber(for_=(IResource, IObjectModifiedEvent))
async def add_object(obj, event):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    type_name = getattr(obj, 'type_name', None)
    if type_name is None or IContainer.providedBy(obj):
        return

    fut = get_future()
    if fut is None:
        return
    search = query_utility(ICatalogUtility)
    if search:
        if IObjectModifiedEvent.providedBy(event):
            indexes = []
            if event.payload and len(event.payload) > 0:
                # get a list of potential indexes
                for field_name in event.payload.keys():
                    if '.' in field_name:
                        for behavior_field_name in event.payload[field_name].keys():
                            indexes.append(behavior_field_name)
                    else:
                        indexes.append(field_name)
                fut.update[uid] = await search.get_data(obj, indexes)
        else:
            fut.index[uid] = await search.get_data(obj)


@configure.subscriber(for_=(IContainer, IObjectAddedEvent))
async def initialize_catalog(container, event):
    search = query_utility(ICatalogUtility)
    if search:
        await search.initialize_catalog(container)


@configure.subscriber(for_=(IContainer, IObjectRemovedEvent))
async def remove_catalog(container, event):
    search = query_utility(ICatalogUtility)
    if search:
        await search.remove_catalog(container)
