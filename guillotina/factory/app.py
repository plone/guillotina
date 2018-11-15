import asyncio
import json
import logging.config
from types import ModuleType
from typing import Optional

import aiotask_context
from aiohttp import web
from guillotina import configure
from guillotina import glogging
from guillotina._settings import app_settings
from guillotina._settings import default_settings
from guillotina.behaviors import apply_concrete_behaviors
from guillotina.component import get_utility
from guillotina.component import provide_utility
from guillotina.configure.config import ConfigurationMachine
from guillotina.content import JavaScriptApplication
from guillotina.content import StaticDirectory
from guillotina.content import StaticFile
from guillotina.content import load_cached_schema
from guillotina.event import notify
from guillotina.events import ApplicationCleanupEvent
from guillotina.events import ApplicationConfiguredEvent
from guillotina.events import ApplicationInitializedEvent
from guillotina.events import DatabaseInitializedEvent
from guillotina.exceptions import ConflictError
from guillotina.exceptions import TIDConflictError
from guillotina.factory.content import ApplicationRoot
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IDatabaseConfigurationFactory
from guillotina.request import Request
from guillotina.response import HTTPConflict
from guillotina.traversal import TraversalRouter
from guillotina.utils import lazy_apply
from guillotina.utils import list_or_dict_items
from guillotina.utils import resolve_dotted_name
from guillotina.utils import resolve_path


RSA: Optional[ModuleType] = None
try:
    from Crypto.PublicKey import RSA
except ImportError:
    pass


logger = glogging.getLogger('guillotina')


def update_app_settings(settings):
    for key, value in settings.items():
        if (isinstance(app_settings.get(key), dict) and
                isinstance(value, dict)):
            app_settings[key].update(value)
        else:
            app_settings[key] = value


def load_application(module, root, settings):
    # includeme function
    if hasattr(module, 'includeme'):
        lazy_apply(module.includeme, root, settings)
    # app_settings
    if hasattr(module, 'app_settings') and app_settings != module.app_settings:
        update_app_settings(module.app_settings)
    # services
    configure.load_all_configurations(root.config, module.__name__)


def configure_application(module_name, config, root, settings, configured):
    if module_name in configured:
        return

    module = resolve_dotted_name(module_name)
    if hasattr(module, 'app_settings') and app_settings != module.app_settings:
        # load dependencies if necessary
        for dependency in module.app_settings.get('applications') or []:
            if dependency not in configured and module_name != dependency:
                configure_application(dependency, config, root, settings, configured)

    config.begin(module_name)
    load_application(module, root, settings)
    config.execute_actions()
    config.commit()

    configured.append(module_name)


class GuillotinaAIOHTTPApplication(web.Application):
    async def _handle(self, request, retries=0):
        aiotask_context.set('request', request)
        try:
            return await super()._handle(request)
        except (ConflictError, TIDConflictError) as e:
            if app_settings.get('conflict_retry_attempts', 3) > retries:
                label = 'DB Conflict detected'
                if isinstance(e, TIDConflictError):
                    label = 'TID Conflict Error detected'
                tid = getattr(getattr(request, '_txn', None), '_tid', 'not issued')
                logger.debug(
                    f'{label}, retrying request, tid: {tid}, retries: {retries + 1})',
                    exc_info=True)
                request._retry_attempt = retries + 1
                request.clear_futures()
                return await self._handle(request, retries + 1)
            logger.error(
                'Exhausted retry attempts for conflict error on tid: {}'.format(
                    getattr(getattr(request, '_txn', None), '_tid', 'not issued')
                ))
            return HTTPConflict()

    def _make_request(self, message, payload, protocol, writer, task,
                      _cls=Request):
        return _cls(
            message, payload, protocol, writer, task,
            self._loop,
            client_max_size=self._client_max_size)


def make_aiohttp_application():
    middlewares = [resolve_dotted_name(m) for m in app_settings.get('middlewares', [])]
    router_klass = app_settings.get('router', TraversalRouter)
    router = resolve_dotted_name(router_klass)()
    return GuillotinaAIOHTTPApplication(
        router=router,
        middlewares=middlewares,
        **app_settings.get('aiohttp_settings', {}))


_dotted_name_settings = (
    'auth_extractors',
    'auth_token_validators',
    'auth_user_identifiers',
    'pg_connection_class',
    'oid_generator',
    'cors_renderer',
    'check_writable_request'
)

def optimize_settings(settings):
    '''
    pre-render settings that come in as strings but are used by the app
    '''
    for name in _dotted_name_settings:
        if name not in settings:
            continue
        val = settings[name]
        if isinstance(val, str):
            settings[name] = resolve_dotted_name(val)
        elif isinstance(val, list):
            new_val = []
            for v in val:
                if isinstance(v, str):
                    v = resolve_dotted_name(v)
                new_val.append(v)
            settings[name] = resolve_dotted_name(new_val)


async def make_app(config_file=None, settings=None, loop=None, server_app=None):

    # reset app_settings
    app_settings.clear()
    app_settings.update(default_settings)

    if loop is None:
        loop = asyncio.get_event_loop()

    # chainmap task factory is actually very important
    # default task factory uses inheritance in a way
    # that bubbles back down. So it's possible for a sub-task
    # to clear out the request of the parent task
    loop.set_task_factory(aiotask_context.chainmap_task_factory)

    if config_file is not None:
        with open(config_file, 'r') as config:
            settings = json.load(config)
    elif settings is None:
        raise Exception('Neither configuration or settings')

    # Create root Application
    root = ApplicationRoot(config_file, loop)
    provide_utility(root, IApplication, 'root')

    # Initialize global (threadlocal) ZCA configuration
    config = root.config = ConfigurationMachine()

    import guillotina
    import guillotina.db.factory
    import guillotina.db.writer
    import guillotina.db.db
    configure.scan('guillotina.renderers')
    configure.scan('guillotina.api')
    configure.scan('guillotina.content')
    configure.scan('guillotina.registry')
    configure.scan('guillotina.auth')
    configure.scan('guillotina.json')
    configure.scan('guillotina.behaviors')
    configure.scan('guillotina.languages')
    configure.scan('guillotina.permissions')
    configure.scan('guillotina.security.security_local')
    configure.scan('guillotina.security.policy')
    configure.scan('guillotina.auth.participation')
    configure.scan('guillotina.catalog.index')
    configure.scan('guillotina.catalog.catalog')
    configure.scan('guillotina.files')
    configure.scan('guillotina.annotations')
    configure.scan('guillotina.constraintypes')
    configure.scan('guillotina.subscribers')
    configure.scan('guillotina.db.strategies')
    configure.scan('guillotina.db.cache')
    configure.scan('guillotina.exc_resp')
    configure.scan('guillotina.fields')
    load_application(guillotina, root, settings)
    config.execute_actions()
    config.commit()

    configured = ['guillotina']
    for module_name in settings.get('applications') or []:
        configure_application(module_name, config, root, settings, configured)

    apply_concrete_behaviors()

    # update *after* plugins loaded
    update_app_settings(settings)

    if 'logging' in app_settings:
        logging.config.dictConfig(app_settings['logging'])

    # Make and initialize aiohttp app
    if server_app is None:
        server_app = make_aiohttp_application()
    root.app = server_app
    server_app.root = root
    server_app.config = config

    optimize_settings(app_settings)

    await notify(ApplicationConfiguredEvent(server_app, loop))

    for key, dbconfig in list_or_dict_items(app_settings['databases']):
        factory = get_utility(
            IDatabaseConfigurationFactory, name=dbconfig['storage'])
        root[key] = await factory(key, dbconfig, loop)
        await notify(DatabaseInitializedEvent(root[key]))

    for key, file_path in list_or_dict_items(app_settings['static']):
        path = resolve_path(file_path).resolve()
        if not path.exists():
            raise Exception('Invalid static directory {}'.format(file_path))
        if path.is_dir():
            root[key] = StaticDirectory(path)
        else:
            root[key] = StaticFile(path)

    for key, file_path in list_or_dict_items(app_settings['jsapps']):
        path = resolve_path(file_path).resolve()
        if not path.exists() or not path.is_dir():
            raise Exception('Invalid jsapps directory {}'.format(file_path))
        root[key] = JavaScriptApplication(path)

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
    server_app.router.set_root(root)
    server_app.on_cleanup.append(cleanup_app)

    for util in app_settings.get('utilities') or []:
        logger.warn('Adding : ' + util['provides'])
        root.add_async_utility(util['provides'], util, loop=loop)

    for key, util in app_settings['load_utilities'].items():
        logger.info('Adding ' + key + ' : ' + util['provides'])
        root.add_async_utility(key, util, loop=loop)

    # Load cached Schemas
    load_cached_schema()

    await notify(ApplicationInitializedEvent(server_app, loop))

    return server_app


async def cleanup_app(app):
    await notify(ApplicationCleanupEvent(app))
    await close_utilities(app)
    await close_dbs(app)


async def close_utilities(app):
    root = get_utility(IApplication, name='root')
    for key in list(root._async_utilities.keys()):
        logger.info('Removing ' + key)
        await root.del_async_utility(key)

async def close_dbs(app):
    root = get_utility(IApplication, name='root')
    for db in root:
        if IDatabase.providedBy(db[1]):
            await db[1].finalize()
