from concurrent.futures import ThreadPoolExecutor
from guillotina.db.reader import reader
from guillotina._settings import app_settings
from guillotina.auth.users import RootUser
from guillotina.auth.validators import hash_password
from guillotina.component import get_adapter
from guillotina.component import get_global_components
from guillotina.component import get_utility
from guillotina.component import provide_utility
from guillotina.const import ROOT_ID
from guillotina.db.interfaces import IDatabaseManager
from guillotina.db.interfaces import IWriter
from guillotina.db.transaction_manager import TransactionManager
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.tests.utils import make_mocked_request
from guillotina.transactions import get_transaction
from guillotina.utils import apply_coroutine
from guillotina.utils import import_class
from guillotina.utils import lazy_apply
from guillotina.utils import list_or_dict_items
from zope.interface import implementer

import asyncio
import logging


logger = logging.getLogger('guillotina')


@implementer(IApplication)
class ApplicationRoot(object):
    executor = ThreadPoolExecutor(max_workers=100)
    root_user = None
    app = None  # set after app configuration is done

    def __init__(self, config_file, loop=None):
        self._items = {}
        self._config_file = config_file
        self._async_utilities = {}
        self._loop = loop

    def add_async_utility(self, key, config, loop=None):
        if key in self._async_utilities:
            logger.warn(
                f'Utility already registered {key}')
            return

        interface = import_class(config['provides'])
        factory = import_class(config['factory'])
        try:
            utility_object = lazy_apply(
                factory, config.get('settings', {}),
                loop=loop or self._loop)
        except Exception:
            logger.error('Error initializing utility {}'.format(repr(factory)),
                         exc_info=True)
            raise
        provide_utility(utility_object, interface)
        if hasattr(utility_object, 'initialize'):
            task = asyncio.ensure_future(
                lazy_apply(utility_object.initialize, app=self.app),
                loop=loop or self._loop)
        else:
            task = None
            logger.warn(f'No initialize method found on {utility_object} object')
        self.add_async_task(key, task, config)

    def add_async_task(self, ident, task, config):
        if ident in self._async_utilities:
            raise KeyError("Already exist an async utility with this id")
        self._async_utilities[ident] = {
            'task': task,
            'config': config
        }

    def cancel_async_utility(self, ident):
        if ident in self._async_utilities:
            if self._async_utilities[ident]['task'] is not None:
                if not self._async_utilities[ident]['task'].done():
                    self._async_utilities[ident]['task'].cancel()
        else:
            raise KeyError("Ident does not exist as utility")

    async def del_async_utility(self, key):
        self.cancel_async_utility(key)
        config = self._async_utilities[key]['config']
        interface = import_class(config['provides'])
        utility = get_utility(interface)
        if hasattr(utility, 'finalize'):
            await lazy_apply(utility.finalize, app=self.app)
        gsm = get_global_components()
        gsm.unregisterUtility(utility, provided=interface)
        del self._async_utilities[key]

    def set_root_user(self, user):
        password = user['password']
        if password:
            password = hash_password(password)
        self.root_user = RootUser(password)

    def __contains__(self, key):
        return True if key in self._items else False

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        return self._items[key]

    async def get(self, key):
        try:
            return self[key]
        except KeyError:
            pass

    def __delitem__(self, key):
        del self._items[key]

    def __iter__(self):
        return iter(self._items.items())

    def __setitem__(self, key, value):
        self._items[key] = value

    async def async_get(self, key, suppress_events=True):
        if key in self._items:
            return self._items[key]
        # check configured storages, see if there is a database registered under this name...
        for _, config in list_or_dict_items(app_settings['storages']):
            manager = config.get('type', config['storage'])
            factory = get_adapter(self, IDatabaseManager,
                                  name=manager, args=[config])
            if await factory.exists(key):
                return await factory.get_database(key)


@implementer(IDatabase)
class Database:

    def __init__(self, key, storage, klass=TransactionManager):
        """
        Create an object database.

        Database object is persistent through the application
        """
        self._storage = storage
        self.id = self._database_name = key
        self._tm = None
        self.transaction_klass = klass

    @property
    def storage(self):
        return self._storage

    async def initialize(self):
        """
        create root object if necessary
        """
        request = make_mocked_request('POST', '/')
        request._db_write_enabled = True
        tm = request._tm = self.get_transaction_manager()
        txn = await tm.begin()

        try:
            await txn._strategy.retrieve_tid()
            root = await tm._storage.load(txn, ROOT_ID)
            if root is not None:
                root = reader(root)
                root._p_jar = txn
                if root.__db_id__ is None:
                    root.__db_id__ = self._database_name
                    await tm._storage.store(ROOT_ID, 0, IWriter(root), root, txn)
        except KeyError:
            from guillotina.db.db import Root
            root = Root(self._database_name)
            await tm._storage.store(ROOT_ID, 0, IWriter(root), root, txn)
        finally:
            await tm.commit(txn=txn)

    async def open(self):
        """Return a database Connection for use by application code.
        """
        return await self._storage.open()

    async def close(self, conn):
        await self._storage.close(conn)

    async def finalize(self):
        await self._storage.finalize()

    def get_transaction_manager(self):
        """
        New transaction manager for every request
        """
        if self._tm is None:
            self._tm = self.transaction_klass(self._storage, self)
        return self._tm

    @property
    def _p_jar(self):
        try:
            txn = get_transaction()
            if txn is None:
                txn = self.get_transaction_manager()._last_txn
            return txn
        except AttributeError:
            return self.get_transaction_manager()._last_txn

    async def get_root(self):
        try:
            return await self._p_jar.get(ROOT_ID)
        except KeyError:
            pass

    async def async_get(self, key, suppress_events=False):
        root = await self.get_root()
        if root is not None:
            return await root.async_get(key)

    async def async_keys(self):
        root = await self.get_root()
        if root is not None:
            return await root._p_jar.keys(root._p_oid)
        return []

    async def async_set(self, key, value):
        root = await self.get_root()
        await root.async_set(key, value)

    async def async_del(self, key):
        root = await self.get_root()
        await apply_coroutine(root._p_jar.delete, await root.async_get(key))

    async def async_items(self):
        root = await self.get_root()
        if root is not None:
            async for key, value in root._p_jar.items(root):
                yield key, value

    async def async_contains(self, key):
        # is there any request active ? -> conn there
        root = await self.get_root()
        if root is not None:
            return await apply_coroutine(root._p_jar.contains, root._p_oid, key)
        return False

    async def async_len(self):
        root = await self.get_root()
        if root is not None:
            return await apply_coroutine(root._p_jar.len, root._p_oid)
        return 0
