# -*- coding: utf-8 -*-
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.content import Site
from plone.server.request import RequestAwareDB
from plone.server.request import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import registerCommonDirectives
import plone.registry
import sys
import transaction
import venusianconfiguration
import ZODB
import zope.component


def make_app():
    app = web.Application(router=TraversalRouter())
    app.executor = ThreadPoolExecutor(max_workers=1)

    venusianconfiguration.enable()
    config = ConfigurationMachine()
    registerCommonDirectives(config)
    venusianconfiguration.configure.include(
        package=zope.component, file='meta.zcml')
    venusianconfiguration.configure.include(
        package=plone.registry)
    venusianconfiguration.venusianscan(sys.modules[__name__], config)
    config.execute_actions()
    app.config = config

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
