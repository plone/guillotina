# -*- coding: utf-8 -*-
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from plone.server.content import site
from plone.server.content import Site
from plone.server.request import RequestAwareDB
from plone.server.request import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from venusianconfiguration import configure
from venusianconfiguration import scan
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import registerCommonDirectives
from zope.component import getUtility
import plone.dexterity
import plone.example
import plone.registry
import sys
import transaction
import venusianconfiguration
import ZODB
import zope.component
from plone.example.todo import ITodo
from plone.dexterity.interfaces import IDexterityFTI

configure.include(package=zope.component, file='meta.zcml')
configure.include(package=plone.registry)
configure.include(package=plone.dexterity, file='meta.zcml')
configure.include(package=plone.dexterity)
configure.include(package=plone.example)


scan(site)


def make_app():
    app = web.Application(router=TraversalRouter())
    app.executor = ThreadPoolExecutor(max_workers=1)

    # ZCA
    venusianconfiguration.enable()   # Enable Python syntax for ZCA
    config = ConfigurationMachine()  # Init machinery
    registerCommonDirectives(config)
    venusianconfiguration.venusianscan(sys.modules[__name__], config)  # Scan
    config.execute_actions()  # Execute (into global registry)
    app.config = config  # Store log

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
