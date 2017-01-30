from plone.server.auth.validators import hash_password
from plone.server.auth.users import RootUser
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.utils import import_class
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import provideUtility
from zope.interface import implementer

import asyncio


@implementer(IApplication)
class ApplicationRoot(object):

    root_user = None

    def __init__(self, config_file):
        self._dbs = {}
        self._config_file = config_file
        self._async_utilities = {}

    def add_async_utility(self, config):
        interface = import_class(config['provides'])
        factory = import_class(config['factory'])
        utility_object = factory(config['settings'])
        provideUtility(utility_object, interface)
        task = asyncio.ensure_future(utility_object.initialize(app=self))
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

    def set_root_user(self, user):
        password = user['password']
        if password:
            password = hash_password(password)
        self.root_user = RootUser(password)

    def __contains__(self, key):
        return True if key in self._dbs else False

    def __len__(self):
        return len(self._dbs)

    def __getitem__(self, key):
        return self._dbs[key]

    def __delitem__(self, key):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        del self._dbs[key]

    def __iter__(self):
        return iter(self._dbs.items())

    def __setitem__(self, key, value):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        self._dbs[key] = value


@implementer(IDatabase)
class Database(object):
    def __init__(self, id, db):
        self.id = id
        self._db = db
        self._conn = None
        self.tm_ = RequestAwareTransactionManager()

    def get_transaction_manager(self):
        return self.tm_

    def open(self):
        tm_ = RequestAwareTransactionManager()
        return self._db.open(transaction_manager=tm_)

    def _open(self):
        self._conn = self._db.open(transaction_manager=self.tm_)

        @self._conn.onCloseCallback
        def on_close():
            self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._open()
        return self._conn

    @property
    def _p_jar(self):
        if self._conn is None:
            self._open()
        return self._conn

    def __getitem__(self, key):
        # is there any request active ? -> conn there
        return self.conn.root()[key]

    def keys(self):
        return list(self.conn.root().keys())

    def __setitem__(self, key, value):
        """ This operation can only be done through HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """
        self.conn.root()[key] = value

    def __delitem__(self, key):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        del self.conn.root()[key]

    def __iter__(self):
        return iter(self.conn.root().items())

    def __contains__(self, key):
        # is there any request active ? -> conn there
        return key in self.conn.root()

    def __len__(self):
        return len(self.conn.root())
