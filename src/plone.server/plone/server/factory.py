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
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from zope.component import getAllUtilitiesRegisteredFor
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives

import asyncio
import sys
import transaction
import ZODB


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
            site = createContent('Plone Site',
                                 id='plone',
                                 title='Demo Site',
                                 description='Awww yeah...')
            dbroot['plone'] = site
            site.__parent__ = None  # don't expose dbroot

            # And some example content
            obj = createContent('Todo',
                                id='obj1',
                                title="It's a todo!",
                                notes='$240 of pudding.')
            site['obj1'] = obj
            obj.__parent__ = site

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
