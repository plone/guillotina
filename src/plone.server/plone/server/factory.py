# -*- coding: utf-8 -*-
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from pkg_resources import iter_entry_points
from plone.dexterity.utils import createContent
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.async import IAsyncUtility
from plone.server.auth.oauth import IPloneJWTExtractionConfig
from plone.server.auth.oauth import IPloneOAuthConfig
from plone.server.content import Site
from plone.server.registry import IAuthExtractionPlugins
from plone.server.registry import IAuthPloneUserPlugins
from plone.server.registry import ILayers
from plone.server.request import RequestAwareDB
from plone.server.request import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from zope.component import getAllUtilitiesRegisteredFor
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives

import asyncio
import functools
import sys
import transaction
import ZODB


def create_site(app, id, title='', description=''):
    plonesite = Site(id)
    app[id] = plonesite
    plonesite.title = title
    plonesite.description = description
    # TODO: This should really get set on the class itself
    plonesite.portal_type = 'Plone Site'

    # Creating and registering a local registry
    plonesite['registry'] = Registry()
    plonesite['registry'].registerInterface(ILayers)
    plonesite['registry'].registerInterface(IAuthPloneUserPlugins)
    plonesite['registry'].registerInterface(IAuthExtractionPlugins)

    plonesite['registry'].forInterface(ILayers).active_layers = \
        ['plone.server.api.layer.IDefaultLayer']

    plonesite['registry'].forInterface(
        IAuthExtractionPlugins).active_plugins = \
        ['plone.server.auth.oauth.PloneJWTExtraction']

    plonesite['registry'].forInterface(
        IAuthPloneUserPlugins).active_plugins = \
        ['plone.server.auth.oauth.OAuthPloneUserFactory']

    # Set default plugins
    plonesite['registry'].registerInterface(IPloneJWTExtractionConfig)
    plonesite['registry'].registerInterface(IPloneOAuthConfig)
    sm = plonesite.getSiteManager()
    sm.registerUtility(plonesite['registry'], provided=IRegistry)

    return plonesite


def make_app():
    # Initialize aiohttp app
    app = web.Application(router=TraversalRouter())

    # Initialize asyncio executor worker
    app.executor = ThreadPoolExecutor(max_workers=1)

    # Initialize global (threadlocal) ZCA configuration
    app.config = ConfigurationMachine()
    registerCommonDirectives(app.config)
    include(app.config, 'configure.zcml', sys.modules['plone.server'])
    for ep in iter_entry_points('plone.server'):  # auto-include applications
        include(app.config, 'configure.zcml', ep.load())
    app.config.execute_actions()

    # Initialize DB
    db = ZODB.DB('Data.fs')
    conn = db.open()
    if getattr(conn.root, 'data', None) is None:
        with transaction.manager:
            dbroot = conn.root()

            # Creating a testing site
            plonesite = create_site(dbroot,
                                    id='plone',
                                    title='Demo Site',
                                    description='Awww yeah...')

            # And some example content
            obj = createContent('Todo',
                                id='obj1',
                                title='It\'s a todo!',
                                notes='$240 of pudding.')
            plonesite['obj1'] = obj
            obj.__parent__ = plonesite

    conn.close()
    db.close()

    for utility in getAllUtilitiesRegisteredFor(IAsyncUtility):
        asyncio.ensure_future(utility.initialize(app=app))

    # Set request aware database for app
    db = RequestAwareDB('Data.fs')
    tm_ = RequestAwareTransactionManager()
    # While _p_jar is a funny name, it's consistent with Persistent API
    app._p_jar = db.open(transaction_manager=tm_)

    # Set router root from the ZODB connection
    app.router.set_root_factory(app._p_jar.root)

    return app
