from aiohttp import web
from guillotina import app_settings
from guillotina import configure
from guillotina import interfaces
from guillotina import languages
from guillotina import logger
from guillotina.async import IAsyncUtility
from guillotina.component import getAllUtilitiesRegisteredFor
from guillotina.component import getUtility
from guillotina.component import provideUtility
from guillotina.configure.config import ConfigurationMachine
from guillotina.content import load_cached_schema
from guillotina.content import StaticDirectory
from guillotina.content import StaticFile
from guillotina.contentnegotiation import ContentNegotiatorUtility
from guillotina.exceptions import ConfigurationConflictError
from guillotina.factory.content import ApplicationRoot
from guillotina.interfaces import IApplication
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IDatabaseConfigurationFactory
from guillotina.interfaces.content import IContentNegotiation
from guillotina.traversal import TraversalRouter
from guillotina.utils import resolve_dotted_name

import asyncio
import collections
import inspect
import json
import os
import pathlib


try:
    from Crypto.PublicKey import RSA
except ImportError:
    RSA = None


def update_app_settings(settings):
    for key, value in settings.items():
        if isinstance(app_settings.get(key), dict):
            app_settings[key].update(value)
        else:
            app_settings[key] = value


def load_application(module, root, settings):
    app = root.app
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
    "default_layer": interfaces.IDefaultLayer,
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
    # pass in tuple to force ordering for default provided renderers here
    # XXX ordering is *required* for some views to work as if no accept
    # header is provided, it'll default to the first type provided
    "renderers": collections.OrderedDict((
        ("application/json", interfaces.IRendererFormatJson),
        ("text/html", interfaces.IRendererFormatHtml)
    )),
    "languages": {
        "en": languages.IEN,
        "en-us": languages.IENUS,
        "ca": languages.ICA
    }
}


def make_app(config_file=None, settings=None, loop=None):
    app_settings.update(_delayed_default_settings)

    if loop is None:
        loop = asyncio.get_event_loop()

    if config_file is not None:
        with open(config_file, 'r') as config:
            settings = json.load(config)
    elif settings is None:
        raise Exception('Neither configuration or settings')

    middlewares = [resolve_dotted_name(m) for m in settings.get('middlewares', [])]
    # Initialize aiohttp app
    app = web.Application(
        router=TraversalRouter(),
        loop=loop,
        middlewares=middlewares)

    # Create root Application
    root = ApplicationRoot(config_file)
    root.app = app
    provideUtility(root, IApplication, 'root')

    # Initialize global (threadlocal) ZCA configuration
    app.config = ConfigurationMachine()

    import guillotina
    import guillotina.db.factory
    import guillotina.db.partition
    import guillotina.db.writer
    import guillotina.db.db
    configure.scan('guillotina.translation')
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
    configure.scan('guillotina.framing')
    configure.scan('guillotina.files')
    configure.scan('guillotina.annotations')
    configure.scan('guillotina.constraintypes')
    configure.scan('guillotina.subscribers')
    load_application(guillotina, root, settings)
    app.config.execute_actions()
    app.config.commit()

    for module_name in settings.get('applications', []):
        app.config.begin(module_name)
        load_application(resolve_dotted_name(module_name), root, settings)
        app.config.execute_actions()
        app.config.commit()

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
            factory = getUtility(
                IDatabaseConfigurationFactory, name=dbconfig['storage'])
            if asyncio.iscoroutinefunction(factory):
                future = asyncio.ensure_future(
                    factory(key, dbconfig, app), loop=app.loop)

                app.loop.run_until_complete(future)
                root[key] = future.result()
            else:
                root[key] = factory(key, dbconfig)

    for static in app_settings['static']:
        for key, file_path in static.items():
            if ':' in file_path:
                # referencing a module
                dotted_mod_name, _, rel_path = file_path.partition(':')
                module = resolve_dotted_name(dotted_mod_name)
                if module is None:
                    raise Exception('Invalid module for static directory {}'.format(file_path))
                file_path = os.path.join(
                    os.path.dirname(os.path.realpath(module.__file__)), rel_path)
            path = pathlib.Path(file_path)
            if not path.exists():
                raise Exception('Invalid static directory {}'.format(file_path))
            if path.is_dir():
                root[key] = StaticDirectory(path)
            else:
                root[key] = StaticFile(path)

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
        # In case there is Utilties that are registered
        ident = asyncio.ensure_future(utility.initialize(app=app), loop=app.loop)
        root.add_async_task(utility, ident, {})

    app.on_cleanup.append(close_utilities)

    for util in app_settings['utilities']:
        root.add_async_utility(util)

    # Load cached Schemas
    load_cached_schema()

    return app


async def close_utilities(app):
    for utility in getAllUtilitiesRegisteredFor(IAsyncUtility):
        asyncio.ensure_future(utility.finalize(app=app), loop=app.loop)
    for db in app.router._root:
        if IDatabase.providedBy(db[1]):
            await db[1]._db.finalize()
