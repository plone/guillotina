from aiohttp import web
from pkg_resources import iter_entry_points
from plone.server import app_settings
from plone.server import configure
from plone.server import interfaces
from plone.server import languages
from plone.server import logger
from plone.server.async import IAsyncUtility
from plone.server.content import load_cached_schema
from plone.server.content import StaticDirectory
from plone.server.content import StaticFile
from plone.server.contentnegotiation import ContentNegotiatorUtility
from plone.server.exceptions import RequestNotFound
from plone.server.factory.content import ApplicationRoot
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from plone.server.interfaces import IDatabaseConfigurationFactory
from plone.server.interfaces.content import IContentNegotiation
from plone.server.traversal import TraversalRouter
from zope.component import getAllUtilitiesRegisteredFor
from zope.component import getUtility
from zope.component import provideUtility
from zope.configuration.config import ConfigurationConflictError
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives

import asyncio
import collections
import inspect
import json
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
    # zcml
    try:
        include(app.config, 'configure.zcml', module)
    except (FileNotFoundError, NotADirectoryError):
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
    configure.scan('plone.server.translation')
    configure.scan('plone.server.renderers')
    configure.scan('plone.server.api')
    configure.scan('plone.server.content')
    configure.scan('plone.server.auth')
    configure.scan('plone.server.json')
    configure.scan('plone.server.behaviors')
    configure.scan('plone.server.languages')
    configure.scan('plone.server.permissions')
    configure.scan('plone.server.migrate.migrations')
    configure.scan('plone.server.auth.checker')
    configure.scan('plone.server.auth.security_local')
    configure.scan('plone.server.auth.policy')
    configure.scan('plone.server.auth.participation')
    configure.scan('plone.server.catalog.index')
    configure.scan('plone.server.catalog.catalog')
    configure.scan('plone.server.framing')
    configure.scan('plone.server.file')
    configure.scan('plone.server.types')
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
            factory = getUtility(
                IDatabaseConfigurationFactory, name=dbconfig['storage'])
            root[key] = factory(key, dbconfig)

    for static in app_settings['static']:
        for key, file_path in static.items():
            path = pathlib.Path(file_path)
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
        # In case there is Utilties that are registered from zcml
        ident = asyncio.ensure_future(utility.initialize(app=app), loop=app.loop)
        root.add_async_utility(ident, {})

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
            try:
                db[1]._db.close()
            except RequestNotFound:
                pass
