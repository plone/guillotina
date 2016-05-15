# -*- coding: utf-8 -*-
import ZODB

from aiohttp import web

from concurrent.futures import ThreadPoolExecutor

from plone.server.content import Container
from plone.server.content import Site
from plone.server.request import RequestAwareDB, RequestAwareTransactionManager
from plone.server.service import ContainerView
from plone.server.traversal import TraversalRouter
from plone.server.traversal.abc import AbstractResource
from plone.server.traversal.traversal import Traverser

from plone.registry import Registry
from plone.registry.interfaces import IRegistry
from zope.component.hooks import setSite

import zope.component
import plone
import transaction
import sys
import venusianconfiguration
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import registerCommonDirectives


class RootFactory(AbstractResource):

    __parent__ = None

    def __init__(self, app):
        self.app = app
        self.root = app._p_jar.root.data

    def __getitem__(self, name):
        # adding the request
        import pdb; pdb.set_trace()
        return Traverser(self, (name,))

    async def get(self, name):
        return await self.root.get(name)


def make_app():
    app = web.Application(router=TraversalRouter())
    app.executor = ThreadPoolExecutor(max_workers=1)
    app.router.set_root_factory(RootFactory)
    app.router.bind_view(Container, ContainerView)

    venusianconfiguration.enable()
    config = ConfigurationMachine()
    registerCommonDirectives(config)
    venusianconfiguration.configure.include(
        package=zope.component, file="meta.zcml")
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
            conn.root.data = Container()
            conn.root._p_changed = 1
            dbroot = conn.root().data
            # Creating a testing site
            dbroot['plone'] = Site()
            dbroot['plone']._p_changed = 1
            plonesite = dbroot['plone']
            plonesite['registry'] = Registry()
            plonesite['registry']._p_changed = 1
            sm = plonesite.getSiteManager()
            sm.registerUtility(plonesite['registry'], provided=IRegistry)
    conn.close()
    db.close()

    # Set request aware database for app
    db = RequestAwareDB('Data.fs')
    tm_ = RequestAwareTransactionManager()
    # While _p_jar is a funny name, it's consistent with Persistent API
    app._p_jar = db.open(transaction_manager=tm_)
    return app
