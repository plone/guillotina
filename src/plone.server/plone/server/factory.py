# -*- coding: utf-8 -*-
from aiohttp import web
from concurrent.futures import ThreadPoolExecutor
from pkg_resources import iter_entry_points
from plone.dexterity.utils import createContent
from plone.server.async import IAsyncUtility
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from zope.component import getAllUtilitiesRegisteredFor
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDataBase
from plone.server.utils import get_current_request
from plone.server.content import StaticFile
from plone.server.auth.participation import RootParticipation
from zope.interface import implementer
from zope.securitypolicy.principalpermission import PrincipalPermissionManager
from zope.securitypolicy.interfaces import IPrincipalPermissionMap
from zope.component import adapter

import asyncio
import json
import os
import hashlib
import sys
import base64
import transaction
import ZODB


@implementer(IApplication)
class ApplicationRoot(object):

    def __init__(self, config_file):
        self._dbs = {}
        self._config_file = config_file

    def set_creator_salt(self, salt):
        self._salt = base64.b64decode(salt)

    def set_creator_password(self, password):
        self._creator_password = base64.b64decode(password)

    def check_token(self, password):
        if self._creator_password == hashlib.pbkdf2_hmac(
                'sha256', bytes(password), self._salt, 100000):
            return True
        else:
            return False

    def root_participation(self, request):
        header_auth = request.headers.get('AUTHORIZATION')
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'bearer':
                token = encoded_token.encode('ascii')
                if self.check_token(token):
                    return RootParticipation()
        return None

    def __contains__(self, key):
        return True if key in self._dbs else False

    def __len__(self):
        return len(self._dbs)

    def __getitem__(self, key):
        return self._dbs[key]

    def __delitem__(self, key):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        del self._dbs[key]

    def __setitem__(self, key, value):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        self._dbs[key] = value


class DataBaseToJson(object):

    def __init__(self, dbo, request):
        self.dbo = dbo

    def __call__(self):
        return self.dbo.keys()


class ApplicationToJson(object):

    def __init__(self, application, request):
        self.application = application

    def __call__(self):
        return list(self.application._dbs.keys())

class DataBaseSpecialPermissions(PrincipalPermissionManager):
    def __init__(self, db):
        super(DataBaseSpecialPermissions, self).__init__()
        self.grantPermissionToPrincipal('plone.AddPortal', 'RootUser')
        self.grantPermissionToPrincipal('plone.GetPortals', 'RootUser')
        self.grantPermissionToPrincipal('plone.AccessContent', 'RootUser')


@implementer(IDataBase)
class DataBase(object):
    def __init__(self, id, db):
        self.id = id
        self._db = db

    def open(self):
        # transaction.TransactionManager
        # tm_ = RequestAwareTransactionManager()
        # While _p_jar is a funny name, it's consistent with Persistent API
        # return self._db.open(transaction_manager=tm_)
        return self._db.open()

    def __getitem__(self, key):
        # is there any request active ? -> conn there
        return get_current_request()._conn.root[key]

    def keys(self):
        conection = get_current_request()._conn
        return dict(conection.root().keys())

    def __setitem__(self, key, value):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """
        get_current_request()._conn.root()[key] = value

    def __contains__(self, key):
        # is there any request active ? -> conn there
        return key in get_current_request()._conn.root


def make_app(config_file):
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

    with open(config_file, 'r') as config:
        settings = json.load(config)
    root = ApplicationRoot(config_file)

    # for database in settings['databases']:
    #     # Initialize DB
    #     if database['storage'] == 'ZODB':
    #         db = ZODB.DB(database['folder'] + 'Data.fs')
    #         conn = db.open()
    #         if getattr(conn.root, 'data', None) is None:
    #             with transaction.manager:
    #                 dbroot = conn.root()

    #                 # Creating a testing site
    #                 site = createContent('Plone Site',
    #                                      id='plone',
    #                                      title='Demo Site',
    #                                      description='Awww yeah...')
    #                 dbroot['plone'] = site
    #                 site.__parent__ = None  # don't expose dbroot

    #                 # And some example content
    #                 # obj = createContent('Todo',
    #                 #                     id='obj1',
    #                 #                     title="It's a todo!",
    #                 #                     notes='$240 of pudding.')
    #                 # site['obj1'] = obj
    #                 # obj.__parent__ = site
    #         conn.close()
    #         db.close()

    for database in settings['databases']:
        for key, dbconfig in database.items():
            if dbconfig['storage'] == 'ZODB':
                # Set request aware database for app
                db = ZODB.DB(dbconfig['folder'] + 'Data.fs')
                dbo = DataBase(key, db)
            root[key] = dbo

    for static in settings['static']:
        for key, file_path in static.items():
            root[key] = StaticFile(file_path)

    root.set_creator_password(settings['creator']['password'])
    root.set_creator_salt(settings['salt'])

    # Set router root from the ZODB connection
    app.router.set_root(root)

    for utility in getAllUtilitiesRegisteredFor(IAsyncUtility):
        asyncio.ensure_future(utility.initialize(app=app))

    return app
