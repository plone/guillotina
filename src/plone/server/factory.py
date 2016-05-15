# -*- coding: utf-8 -*-
import ZODB

from aiohttp import web

from concurrent.futures import ThreadPoolExecutor

from plone.server.content import Container
from plone.server.request import RequestAwareDB, RequestAwareTransactionManager
from plone.server.service import ContainerView
from plone.server.traversal import TraversalRouter
from plone.server.traversal.abc import AbstractResource
from plone.server.traversal.traversal import Traverser

import transaction


class RootFactory(AbstractResource):

    __parent__ = None

    def __init__(self, app):
        self.app = app
        self.root = app._p_jar.root.data

    def __getitem__(self, name):
        return Traverser(self, (name,))

    async def __getchild__(self, name):
        return await self.root.__getchild__(name)


def make_app():
    app = web.Application(router=TraversalRouter())
    app.executor = ThreadPoolExecutor(max_workers=1)
    app.router.set_root_factory(RootFactory)
    app.router.bind_view(Container, ContainerView)

    # Initialize DB
    db = ZODB.DB('Data.fs')
    conn = db.open()
    if getattr(conn.root, 'data', None) is None:
        with transaction.manager:
            conn.root.data = Container()
            conn.root._p_changed = 1
    conn.close()
    db.close()

    # Set request aware database for app
    db = RequestAwareDB('Data.fs')
    tm_ = RequestAwareTransactionManager()
    # While _p_jar is a funny name, it's consistent with Persistent API
    app._p_jar = db.open(transaction_manager=tm_)
    return app
