from guillotina import configure
from guillotina._settings import app_settings
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
from guillotina.utils import execute
from guillotina.utils import find_container


class Indexer:
    def __init__(self, container):
        self.remove = []
        self.index = {}
        self.update = {}
        self.container = container

    @classmethod
    def get(self):
        return execute.get_future("indexer")

    def register(self):
        execute.add_future("indexer", self)

    async def __call__(self):
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

    async def reindex_security(self, obj):
        reindex_in_future(obj, True)

    index_object_move = reindex_security

    async def remove_object(self, obj):
        self.remove.append(obj)
        uid = obj.uuid
        if uid in self.index:
            del self.index[uid]
        if uid in self.update:
            del self.update[uid]

    async def add_object(self, obj, indexes=None, modified=False, security=False):
        uid = obj.uuid
        search = query_utility(ICatalogUtility)
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
                if uid in self.update:
                    self.update[uid].update(data)
                else:
                    self.update[uid] = data
        else:
            self.index[uid] = await search.get_data(obj)


def get_indexer(context=None):
    search = query_utility(ICatalogUtility)
    if not search:
        return  # no search configured

    klass = app_settings["indexer"]
    indexer = klass.get()
    if indexer is None:
        container = find_container(context)
        if container is None:
            return
        indexer = klass(container)
        indexer.register()
    return indexer


@configure.subscriber(for_=(IResource, IObjectPermissionsModifiedEvent), priority=1000)
async def security_changed(obj, event):
    if IGroupFolder.providedBy(obj):
        # assuming permissions for group are already handled correctly with search
        await index_object(obj, modified=True, security=True)
        return
    fut = get_indexer(obj)
    if fut is not None:
        await fut.reindex_security(obj)


@configure.subscriber(for_=(IResource, IObjectMovedEvent), priority=1000)
async def moved_object(obj, event):
    fut = get_indexer(obj)
    if fut is not None:
        await fut.index_object_move(obj)


@configure.subscriber(for_=(IResource, IObjectRemovedEvent))
async def remove_object(obj, event):
    uid = getattr(obj, "uuid", None)
    if uid is None:
        return
    type_name = getattr(obj, "type_name", None)
    if type_name is None or IContainer.providedBy(obj):
        return

    fut = get_indexer(obj)
    if fut is None:
        return
    await fut.remove_object(obj)


@configure.subscriber(for_=(IResource, IObjectAddedEvent), priority=1000)
@configure.subscriber(for_=(IResource, IObjectModifiedEvent), priority=1000)
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
                if "." in field_name:
                    value = payload[field_name]
                    if not isinstance(value, dict):
                        continue
                    for behavior_field_name in value.keys():
                        indexes.append(behavior_field_name)
                else:
                    indexes.append(field_name)

    await index_object(obj, indexes, modified)


async def index_object(obj, indexes=None, modified=False, security=False):
    uid = getattr(obj, "uuid", None)
    if uid is None:
        return
    type_name = getattr(obj, "type_name", None)
    if type_name is None or IContainer.providedBy(obj):
        return

    fut = get_indexer(obj)
    if fut is None:
        return

    await fut.add_object(obj, indexes, modified, security)


@configure.subscriber(for_=(IContainer, IObjectAddedEvent), priority=1000)
async def initialize_catalog(container, event):
    search = query_utility(ICatalogUtility)
    if search:
        await search.initialize_catalog(container)


@configure.subscriber(for_=(IContainer, IObjectRemovedEvent))
async def remove_catalog(container, event):
    search = query_utility(ICatalogUtility)
    if search:
        await search.remove_catalog(container)
