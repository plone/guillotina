from guillotina import configure
from guillotina.catalog.utils import reindex_in_future
from guillotina.component import query_adapter
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
from guillotina.interfaces import ISecurityInfo
from guillotina.utils import apply_coroutine
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


@configure.subscriber(
    for_=(IResource, IObjectPermissionsModifiedEvent), priority=1000)
async def security_changed(obj, event):
    if IGroupFolder.providedBy(obj):
        # assuming permissions for group are already handled correctly with search
        await index_object(obj, modified=True, security=True)
        return
    # We need to reindex the objects below
    request = get_current_request()
    reindex_in_future(obj, request, True)


@configure.subscriber(
    for_=(IResource, IObjectMovedEvent), priority=1000)
def moved_object(obj, event):
    request = get_current_request()
    reindex_in_future(obj, request, True)


@configure.subscriber(for_=(IResource, IObjectRemovedEvent))
def remove_object(obj, event):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    type_name = getattr(obj, 'type_name', None)
    if type_name is None or IContainer.providedBy(obj):
        return

    fut = get_future()
    if fut is None:
        return

    fut.remove.append(obj)
    if uid in fut.index:
        del fut.index[uid]
    if uid in fut.update:
        del fut.update[uid]


@configure.subscriber(
    for_=(IResource, IObjectAddedEvent), priority=1000)
@configure.subscriber(
    for_=(IResource, IObjectModifiedEvent), priority=1000)
async def add_object(obj, event=None, modified=None, payload=None):
    if modified is None:
        modified = IObjectModifiedEvent.providedBy(event)
    if payload is None and event is not None:
        payload = event.payload
    indexes = None
    if modified:
        indexes = []
        if payload and len(payload) > 0:
            # get a list of potential indexes
            for field_name in payload.keys():
                if '.' in field_name:
                    for behavior_field_name in payload[field_name].keys():
                        indexes.append(behavior_field_name)
                else:
                    indexes.append(field_name)

    await index_object(obj, indexes, modified)


async def index_object(obj, indexes=None, modified=False, security=False):
    uid = getattr(obj, 'uuid', None)
    if uid is None:
        return
    type_name = getattr(obj, 'type_name', None)
    if type_name is None or IContainer.providedBy(obj):
        return

    search = query_utility(ICatalogUtility)
    if search is None:
        return

    fut = get_future()
    if fut is None:
        return

    if modified:
        data = {}
        if security:
            adapter = query_adapter(obj, ISecurityInfo)
            if adapter is not None:
                data = await apply_coroutine(adapter)
        else:
            if indexes is not None and len(indexes) > 0:
                data = await search.get_data(obj, indexes)
        if len(data) > 0:
            if uid in fut.update:
                fut.update[uid].update(data)
            else:
                fut.update[uid] = data
    else:
        fut.index[uid] = await search.get_data(obj)


@configure.subscriber(
    for_=(IContainer, IObjectAddedEvent), priority=1000)
async def initialize_catalog(container, event):
    search = query_utility(ICatalogUtility)
    if search:
        await search.initialize_catalog(container)


@configure.subscriber(for_=(IContainer, IObjectRemovedEvent))
async def remove_catalog(container, event):
    search = query_utility(ICatalogUtility)
    if search:
        await search.remove_catalog(container)
