# -*- coding: utf-8 -*-
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from pkg_resources import iter_entry_points
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.content import Site
from plone.server.request import RequestAwareDB
from plone.server.request import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives
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
            dbroot['plone'] = Site()
            plonesite = dbroot['plone']

            # Creating and registering a local registry
            plonesite['registry'] = Registry()
            sm = plonesite.getSiteManager()
            from plone.dexterity.fti import register, DexterityFTI
            from plone.dexterity import utils
            fti = DexterityFTI('Todo')
            register(fti)
            obj = utils.createContent('Todo')
            plonesite['obj1'] = obj
            sm.registerUtility(plonesite['registry'], provided=IRegistry)

    conn.close()
    db.close()

    # Set request aware database for app
    db = RequestAwareDB('Data.fs')
    tm_ = RequestAwareTransactionManager()
    # While _p_jar is a funny name, it's consistent with Persistent API
    app._p_jar = db.open(transaction_manager=tm_)
    app.router.set_root_factory(app._p_jar.root)
    return app
