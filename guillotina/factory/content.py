from concurrent.futures import ThreadPoolExecutor
from guillotina.auth.users import RootUser
from guillotina.auth.validators import hash_password
from guillotina.component import getGlobalSiteManager
from guillotina.component import getUtility
from guillotina.component import provideUtility
from guillotina.db import ROOT_ID
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.utils import apply_coroutine
from guillotina.utils import import_class
from zope.interface import implementer

import asyncio
import logging


logger = logging.getLogger('guillotina')


@implementer(IApplication)
class ApplicationRoot(object):
    executor = ThreadPoolExecutor(max_workers=100)
    root_user = None

    def __init__(self, config_file):
        self._items = {}
        self._config_file = config_file
        self._async_utilities = {}

    def add_async_utility(self, config, loop=None):
        interface = import_class(config['provides'])
        factory = import_class(config['factory'])
        try:
            utility_object = factory(config['settings'], loop=loop)
        except Exception:
            logger.error('Error initializing utility {}'.format(repr(factory)),
                         exc_info=True)
            raise
        provideUtility(utility_object, interface)
        task = asyncio.ensure_future(utility_object.initialize(app=self.app), loop=loop)
        self.add_async_task(config['provides'], task, config)

    def add_async_task(self, ident, task, config):
        if ident in self._async_utilities:
            raise KeyError("Already exist an async utility with this id")
        self._async_utilities[ident] = {
            'task': task,
            'config': config
        }

    def cancel_async_utility(self, ident):
        if ident in self._async_utilities:
            self._async_utilities[ident]['task'].cancel()
        else:
            raise KeyError("Ident does not exist as utility")

    def del_async_utility(self, config):
        self.cancel_async_utility(config['provides'])
        interface = import_class(config['provides'])
        utility = getUtility(interface)
        gsm = getGlobalSiteManager()
        gsm.unregisterUtility(utility, provided=interface)
        del self._async_utilities[config['provides']]

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
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a db
        XXX TODO
        """

        del self._items[key]

    def __iter__(self):
        return iter(self._items.items())

    def __setitem__(self, key, value):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a db
        XXX TODO
        """

        self._items[key] = value

    async def asyncget(self, key):
        return self._items[key]


@implementer(IDatabase)
class Database(object):
    def __init__(self, id, db):
        self.id = id
        self._db = db
        self._conn = None

    def get_transaction_manager(self):
        return self._db.get_transaction_manager()

    @property
    def _p_jar(self):
        return self.get_transaction_manager()._last_txn

    async def get_root(self):
        return await self._p_jar.get(ROOT_ID)

    async def async_get(self, key):
        root = await self.get_root()
        return await root.async_get(key)

    async def async_keys(self):
        root = await self.get_root()
        return await root._p_jar.keys(root._p_oid)

    async def async_set(self, key, value):
        """ This operation can only be done through HTTP request

        We can check if there is permission to delete a container?
        XXX TODO
        """
        root = await self.get_root()
        await root.async_set(key, value)

    async def async_del(self, key):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a container
        XXX TODO
        """
        root = await self.get_root()
        await apply_coroutine(root._p_jar.delete, await root.async_get(key))

    async def async_items(self):
        root = await self.get_root()
        async for key, value in root._p_jar.items(root):
            yield key, value

    async def async_contains(self, key):
        # is there any request active ? -> conn there
        root = await self.get_root()
        return await apply_coroutine(root._p_jar.contains, root._p_oid, key)

    async def async_len(self):
        root = await self.get_root()
        return await apply_coroutine(root._p_jar.len, root._p_oid)
