# -*- coding: utf-8 -*-
from aiohttp import web
from pkg_resources import iter_entry_points
from plone.server import app_settings
from plone.server import configure
from plone.server import interfaces
from plone.server import languages
from plone.server import logger
from plone.server.async import IAsyncUtility
from plone.server.auth.users import ANONYMOUS_USER_ID
from plone.server.auth.users import ROOT_USER_ID
from plone.server.auth.users import RootUser
from plone.server.auth.validators import hash_password
from plone.server.content import IStaticDirectory
from plone.server.content import IStaticFile
from plone.server.content import load_cached_schema
from plone.server.content import StaticFile
from plone.server.contentnegotiation import ContentNegotiatorUtility
from plone.server.interfaces import IApplication
from plone.server.interfaces import IContentNegotiation
from plone.server.interfaces import IDatabase
from plone.server.interfaces import IRequest
from plone.server.interfaces import IResourceSerializeToJson
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from plone.server.utils import import_class
from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from ZODB.DemoStorage import DemoStorage
from zope.component import getAllUtilitiesRegisteredFor
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import provideUtility
from zope.configuration.config import ConfigurationConflictError
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.securitypolicy.interfaces import IPrincipalPermissionManager
from zope.securitypolicy.principalpermission import PrincipalPermissionManager

import asyncio
import collections
import inspect
import json
import transaction
import ZODB.FileStorage


try:
    from relstorage.options import Options
    from relstorage.storage import RelStorage
    RELSTORAGE = True
except ImportError:
    RELSTORAGE = False

try:
    import newt.db
    NEWT = True
except ImportError:
    NEWT = False

try:
    from Crypto.PublicKey import RSA
except ImportError:
    RSA = None


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


@configure.adapter(
    for_=(IDatabase, IRequest),
    provides=IResourceSerializeToJson)
class DatabaseToJson(object):

    def __init__(self, dbo, request):
        self.dbo = dbo

    def __call__(self):
        return {
            'sites': list(self.dbo.keys())
        }


@configure.adapter(
    for_=(IApplication, IRequest),
    provides=IResourceSerializeToJson)
class ApplicationToJson(object):

    def __init__(self, application, request):
        self.application = application
        self.request = request

    def __call__(self):
        result = {
            'databases': [],
            'static_file': [],
            'static_directory': []
        }

        allowed = self.request.security.checkPermission(
            'plone.GetDatabases', self.application)

        for x in self.application._dbs.keys():
            if IDatabase.providedBy(self.application._dbs[x]) and allowed:
                result['databases'].append(x)
            if IStaticFile.providedBy(self.application._dbs[x]):
                result['static_file'].append(x)
            if IStaticDirectory.providedBy(self.application._dbs[x]):
                result['static_directory'].append(x)
        return result


@configure.adapter(for_=IDatabase, provides=IPrincipalPermissionManager, trusted=True)
@configure.adapter(for_=IApplication, provides=IPrincipalPermissionManager, trusted=True)
class RootSpecialPermissions(PrincipalPermissionManager):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Plone sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, db):
        super(RootSpecialPermissions, self).__init__()
        self.grantPermissionToPrincipal('plone.AddPortal', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.GetPortals', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.DeletePortals', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.AccessContent', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.GetDatabases', ROOT_USER_ID)
        self.grantPermissionToPrincipal('plone.GetAPIDefinition', ROOT_USER_ID)
        # Access anonymous - needs to be configurable
        self.grantPermissionToPrincipal(
            'plone.AccessContent', ANONYMOUS_USER_ID)


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


async def close_utilities(app):
    for utility in getAllUtilitiesRegisteredFor(IAsyncUtility):
        asyncio.ensure_future(utility.finalize(app=app), loop=app.loop)


def update_app_settings(settings):
    for key, value in settings.items():
        if isinstance(app_settings.get(key), dict):
            app_settings[key].update(value)
        else:
            app_settings[key] = value


def load_application(module, root, settings):
    app = root.app
    # zcml
    try:
        include(app.config, 'configure.zcml', module)
    except FileNotFoundError:
        # addons do not need to have zcml
        pass
    # includeme function
    if hasattr(module, 'includeme'):
        args = [root]
        if len(inspect.getargspec(module.includeme).args) == 2:
            args.append(settings)
        module.includeme(*args)
    # app_settings
    if hasattr(module, 'app_settings') and app_settings != module.app_settings:
        update_app_settings(module.app_settings)
    # services
    configure.load_all_configurations(app.config, module.__name__)


# XXX use this to delay imports for these settings
_delayed_default_settings = {
    "default_layers": [
        interfaces.IDefaultLayer
    ],
    "http_methods": {
        "PUT": interfaces.IPUT,
        "POST": interfaces.IPOST,
        "PATCH": interfaces.IPATCH,
        "DELETE": interfaces.IDELETE,
        "GET": interfaces.IGET,
        "OPTIONS": interfaces.IOPTIONS,
        "HEAD": interfaces.IHEAD,
        "CONNECT": interfaces.ICONNECT
    },
    "renderers": collections.OrderedDict({
        "application/json": interfaces.IRendererFormatJson,
        "text/html": interfaces.IRendererFormatHtml,
        "*/*": interfaces.IRendererFormatRaw
    }),
    "languages": {
        "en": languages.IEN,
        "en-us": languages.IENUS,
        "ca": languages.ICA
    }
}


def make_app(config_file=None, settings=None):
    app_settings.update(_delayed_default_settings)

    # Initialize aiohttp app
    app = web.Application(router=TraversalRouter())

    # Create root Application
    root = ApplicationRoot(config_file)
    root.app = app
    provideUtility(root, IApplication, 'root')

    # Initialize global (threadlocal) ZCA configuration
    app.config = ConfigurationMachine()
    registerCommonDirectives(app.config)

    if config_file is not None:
        with open(config_file, 'r') as config:
            settings = json.load(config)
    elif settings is None:
        raise Exception('Neither configuration or settings')

    import plone.server
    configure.include("zope.component")
    configure.include("zope.annotation")
    configure.include("plone.server", "meta.zcml")  # bbb
    configure.scan('..translation')
    configure.scan('..renderers')
    configure.scan('..api')
    configure.scan('..content')
    configure.scan('..security')
    configure.scan('..json')
    configure.scan('..behaviors')
    configure.scan('..languages')
    configure.scan('..permissions')
    configure.scan('..migrate.migrations')
    configure.scan('..auth.participation')
    configure.scan('..auth.principalrole')
    configure.scan('..catalog.index')
    configure.scan('..catalog.catalog')
    configure.scan('..framing')
    configure.scan('..file')
    configure.scan('..types')
    load_application(plone.server, root, settings)

    for ep in iter_entry_points('plone.server'):
        # auto-include applications
        # What an "app" include consists of...
        # 1. load zcml if present
        # 2. load "includeme" module function if present
        # 3. load app_settings dict if present in the module
        if ep.module_name not in settings.get('applications', []):
            continue

        load_application(ep.load(), root, settings)
    try:
        app.config.execute_actions()
    except ConfigurationConflictError as e:
        logger.error(str(e._conflicts))
        raise e

    # XXX we clear now to save some memory
    # it's unclear to me if this is necesary or not but it seems to me that
    # we don't need things registered in both components AND here.
    configure.clear()

    # update *after* plugins loaded
    update_app_settings(settings)

    content_type = ContentNegotiatorUtility(
        'content_type', app_settings['renderers'].keys())
    language = ContentNegotiatorUtility(
        'language', app_settings['languages'].keys())

    provideUtility(content_type, IContentNegotiation, 'content_type')
    provideUtility(language, IContentNegotiation, 'language')

    for database in app_settings['databases']:
        for key, dbconfig in database.items():
            config = dbconfig.get('configuration', {})
            if dbconfig['storage'] == 'ZODB':
                # Open it not Request Aware so it creates the root object
                fs = ZODB.FileStorage.FileStorage(dbconfig['path'])

                db = DB(fs)
                try:
                    rootobj = db.open().root()
                    if not IDatabase.providedBy(rootobj):
                        alsoProvides(rootobj, IDatabase)
                    transaction.commit()
                    rootobj = None
                except:
                    pass
                finally:
                    db.close()
                # Set request aware database for app
                db = RequestAwareDB(dbconfig['path'], **config)
                dbo = Database(key, db)
            elif dbconfig['storage'] == 'ZEO':
                # Try to open it normal to create the root object
                address = (dbconfig['address'], dbconfig['port'])

                zeoconfig = dbconfig.get('zeoconfig', {})
                cs = ClientStorage(address, **zeoconfig)
                db = DB(cs)

                try:
                    conn = db.open()
                    rootobj = conn.root()
                    if not IDatabase.providedBy(rootobj):
                        alsoProvides(rootobj, IDatabase)
                    transaction.commit()
                except:
                    pass
                finally:
                    rootobj = None
                    conn.close()
                    db.close()

                # Set request aware database for app
                cs = ClientStorage(address, **zeoconfig)
                db = RequestAwareDB(cs, **config)
                dbo = Database(key, db)
            elif dbconfig['storage'] == 'RELSTORAGE' and RELSTORAGE:
                options = Options(**dbconfig['options'])
                if dbconfig['type'] == 'postgres':
                    from relstorage.adapters.postgresql import PostgreSQLAdapter
                    dsn = "dbname={dbname} user={username} host={host} password={password} port={port}".format(**dbconfig['dsn'])
                    adapter = PostgreSQLAdapter(dsn=dsn, options=options)
                rs = RelStorage(adapter=adapter, options=options)
                db = DB(rs)
                try:
                    conn = db.open()
                    rootobj = conn.root()
                    if not IDatabase.providedBy(rootobj):
                        alsoProvides(rootobj, IDatabase)
                    transaction.commit()
                except:
                    pass
                finally:
                    rootobj = None
                    conn.close()
                    db.close()
                rs = RelStorage(adapter=adapter, options=options)
                db = RequestAwareDB(rs, **config)
                dbo = Database(key, db)
            elif dbconfig['storage'] == 'NEWT' and NEWT:
                options = Options(**dbconfig['options'])
                if dbconfig['type'] == 'postgres':
                    from relstorage.adapters.postgresql import PostgreSQLAdapter
                    dsn = "dbname={dbname} user={username} host={host} password={password} port={port}".format(**dbconfig['dsn'])
                    adapter = PostgreSQLAdapter(dsn=dsn, options=options)
                rs = RelStorage(adapter=adapter, options=options)
                db = DB(rs)
                try:
                    conn = db.open()
                    rootobj = conn.root()
                    if not IDatabase.providedBy(rootobj):
                        alsoProvides(rootobj, IDatabase)
                    transaction.commit()
                except:
                    pass
                finally:
                    rootobj = None
                    conn.close()
                    db.close()
                rs = RelStorage(adapter=adapter, options=options)
                db = newt.db._db.NewtDB(RequestAwareDB(rs, **config))
                dbo = Database(key, db)
            elif dbconfig['storage'] == 'DEMO':
                storage = DemoStorage(name=dbconfig['name'])
                db = DB(storage)
                alsoProvides(db.open().root(), IDatabase)
                transaction.commit()
                db.close()
                # Set request aware database for app
                db = RequestAwareDB(storage)
                dbo = Database(key, db)
            root[key] = dbo

    for static in app_settings['static']:
        for key, file_path in static.items():
            root[key] = StaticFile(file_path)

    root.set_root_user(app_settings['root_user'])

    if RSA is not None and not app_settings.get('rsa'):
        key = RSA.generate(2048)
        pub_jwk = {'k': key.publickey().exportKey('PEM')}
        priv_jwk = {'k': key.exportKey('PEM')}
        app_settings['rsa'] = {
            'pub': pub_jwk,
            'priv': priv_jwk
        }

    # Set router root
    app.router.set_root(root)

    for utility in getAllUtilitiesRegisteredFor(IAsyncUtility):
        # In case there is Utilties that are registered from zcml
        ident = asyncio.ensure_future(utility.initialize(app=app), loop=app.loop)
        root.add_async_utility(ident, {})

    app.on_cleanup.append(close_utilities)

    for util in app_settings['utilities']:
        root.add_async_utility(util)

    # Load cached Schemas
    load_cached_schema()

    return app
