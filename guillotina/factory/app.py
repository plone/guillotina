from aiohttp import web
from copy import deepcopy
from guillotina import configure
from guillotina import glogging
from guillotina._settings import app_settings
from guillotina._settings import default_settings
from guillotina.behaviors import apply_concrete_behaviors
from guillotina.component import get_utility
from guillotina.component import provide_utility
from guillotina.configure.config import ConfigurationMachine
from guillotina.content import JavaScriptApplication
from guillotina.content import load_cached_schema
from guillotina.content import StaticDirectory
from guillotina.content import StaticFile
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
from guillotina.utils import secure_passphrase
from jwcrypto import jwk

import aiotask_context
import asyncio
import json
import logging.config


logger = glogging.getLogger('guillotina')


def update_app_settings(settings):
    for key, value in settings.items():
        if (isinstance(app_settings.get(key), dict) and
                isinstance(value, dict)):
            app_settings[key].update(value)
        else:
            app_settings[key] = value


class ApplicationConfigurator:

    def __init__(self, applications, config, root, settings, configured=None):
        if configured is None:
            configured = []
        # remove duplicates
        self.applications = list(dict.fromkeys(applications))
        self.configured = configured
        self.config = config
        self.root = root
        self.settings = settings

    def load_application(self, module):
        # includeme function
        if hasattr(module, 'includeme'):
            lazy_apply(module.includeme, self.root, self.settings)
        # app_settings
        if hasattr(module, 'app_settings') and app_settings != module.app_settings:
            update_app_settings(module.app_settings)

        # exclude configuration from sub packages that are registered
        # as applications
        excluded_modules = [
            module_name for module_name in
            set(self.applications) - set([module.__name__])
            if not module.__name__.startswith(module_name)]

        # services
        return configure.load_all_configurations(
            self.root.config, module.__name__, excluded_modules)

    def configure_application(self, module_name):
        if module_name in self.configured:
            return

        module = resolve_dotted_name(module_name)
        if hasattr(module, 'app_settings') and app_settings != module.app_settings:
            # load dependencies if necessary
            for dependency in module.app_settings.get('applications') or []:
                if dependency not in self.configured and module_name != dependency:
                    self.configure_application(dependency)

        self.config.begin(module_name)
        self.load_application(module)
        self.config.execute_actions()
        self.config.commit()

        self.configured.append(module_name)

    def configure_all_applications(self):
        for module_name in self.applications:
            self.configure_application(module_name)


def configure_application(module_name, config, root, settings, configured):
    app_configurator = ApplicationConfigurator(
        [module_name], config, root, settings, configured)
    app_configurator.configure_application(module_name)


def load_application(module, root, settings):
    app_configurator = ApplicationConfigurator(
        [module.__name__], None, root, settings)
    app_configurator.load_application(module)


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
    '''
    Make application from configuration

    :param config_file: path to configuration file to load
    :param settings: dictionary of settings
    :param loop: if not using with default event loop
    :param settings: provide your own aiohttp application
    '''
    # reset app_settings
    startup_vars = {}
    for key in app_settings.keys():
        if key[0] == '_':
            startup_vars[key] = app_settings[key]

    app_settings.clear()
    app_settings.update(startup_vars)
    app_settings.update(deepcopy(default_settings))

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

    app_configurator = ApplicationConfigurator(
        settings.get('applications') or [],
        config, root, settings
    )

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
    configure.scan('guillotina.db.writer')
    configure.scan('guillotina.db.factory')
    configure.scan('guillotina.exc_resp')
    configure.scan('guillotina.fields')
    configure.scan('guillotina.migrations')

    # always load guillotina
    app_configurator.configure_application('guillotina')
    app_configurator.configure_all_applications()

    apply_concrete_behaviors()

    # update *after* plugins loaded
    update_app_settings(settings)

    if 'logging' in app_settings:
        try:
            logging.config.dictConfig(app_settings['logging'])
        except Exception:
            logger.error('Could not setup logging configuration', exc_info=True)

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

    if app_settings.get('jwk') and\
            app_settings.get('jwk').get('k') and\
            app_settings.get('jwk').get('kty'):
        key = jwk.JWK.from_json(json.dumps(app_settings.get('jwk')))
        app_settings['jwk'] = key
        # {"k":"QqzzWH1tYqQO48IDvW7VH7gvJz89Ita7G6APhV-uLMo","kty":"oct"}

    if not app_settings.get('debug') and app_settings['jwt'].get('secret'):
        # validate secret
        secret = app_settings['jwt']['secret']
        if secret == 'secret':
            logger.warning(
                'You are using a very insecure secret key in production mode. '
                'It is strongly advised that you provide a better value for '
                '`jwt.secret` in your config.')
        elif not secure_passphrase(app_settings['jwt']['secret']):
            logger.warning(
                'You are using a insecure secret key in production mode. '
                'It is recommended that you provide a more complex value for '
                '`jwt.secret` in your config.')

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
