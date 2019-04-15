import typing

import aiotask_context
from guillotina._settings import app_settings
from guillotina.component import get_multi_adapter
from guillotina.db.interfaces import ITransaction
from guillotina.exceptions import RequestNotFound
from guillotina.interfaces import ACTIVE_LAYERS_KEY
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IResource
from guillotina.interfaces import IParticipation
from guillotina.security.policy import Interaction
from guillotina.registry import REGISTRY_DATA_KEY
from guillotina.tests.utils import get_mocked_request
from guillotina.utils import get_current_request
from guillotina.utils import get_object_url
from guillotina.utils import import_class
from guillotina.utils import navigate_to
from zope.interface import alsoProvides

from guillotina.auth.users import RootUser


async def login(request, user):
    request.security = Interaction(request)
    request._cache_user = user
    participation = IParticipation(request)
    await participation()
    request.security.add(participation)
    request.security.invalidate_cache()
    request._cache_groups = {}

def logout(request):
    request.security = None
    request._cache_groups = {}
    request._cache_user = None


class ContentAPI:

    def __init__(self, db, user=RootUser('root')):
        self.db = db
        self.tm = db.get_transaction_manager()
        self.request = get_mocked_request()
        self.user = user
        self.request._tm = self.tm
        self.request._db_id = db.id
        self._active_txn = None

    async def __aenter__(self):
        try:
            self._existing_request = get_current_request()
        except RequestNotFound:
            self._existing_request = None
        aiotask_context.set('request', self.request)
        await login(self.request, self.user)
        return self

    async def __aexit__(self, *args):
        logout(self.request)
        aiotask_context.set('request', self._existing_request)
        # make sure to close out connection
        await self.abort()

    async def use_container(self, container: IResource):
        self.request.container = container
        self.request._container_id = container.id
        annotations_container = IAnnotations(container)
        self.request.container_settings = await annotations_container.async_get(
            REGISTRY_DATA_KEY)
        layers = self.request.container_settings.get(ACTIVE_LAYERS_KEY, [])
        for layer in layers:
            alsoProvides(self.request, import_class(layer))

    async def get_transaction(self) -> ITransaction:
        if self._active_txn is None:
            self._active_txn = await self.tm.begin(self.request)
            self.request._txn = self._active_txn
        return self._active_txn

    async def create(self, payload: dict, in_: IResource=None) -> IResource:
        await self.get_transaction()
        if in_ is None:
            in_ = self.db
        view = get_multi_adapter(
            (in_, self.request), app_settings['http_methods']['POST'], name='')

        async def json():
            return payload

        self.request.json = json
        resp = await view()
        await self.commit()
        path = resp.headers['Location']
        if path.startswith('http://') or path.startswith('https://'):
            # strip off container prefix
            container_url = get_object_url(in_, self.request)  # type: ignore
            path = path[len(container_url or ''):]
        return await navigate_to(in_, path.strip('/'))  # type: ignore

    async def get(self, path: str, in_: IResource=None) -> typing.Optional[IResource]:
        await self.get_transaction()
        if in_ is None:
            in_ = self.db
        try:
            return await navigate_to(in_, path.strip('/'))  # type: ignore
        except KeyError:
            return None

    async def delete(self, ob):
        await self.get_transaction()
        parent = ob.__parent__
        await parent.async_del(ob.__name__)
        await self.commit()

    async def commit(self):
        if self._active_txn is None:
            return
        await self.tm.commit(txn=self._active_txn)
        self.request.execute_futures()
        self._active_txn = None
        await self.get_transaction()

    async def abort(self):
        if self._active_txn is None:
            return
        await self.tm.abort(txn=self._active_txn)
        self._active_txn = None
        await self.get_transaction()
