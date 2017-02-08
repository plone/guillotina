from plone.server import configure
from plone.server.factory.content import Database
from plone.server.interfaces import IDatabase
from plone.server.interfaces import IDatabaseConfigurationFactory
from plone.server.transactions import RequestAwareDB
from ZODB.DB import DB
from ZODB.DemoStorage import DemoStorage
from zope.interface import alsoProvides

import transaction
import ZODB.FileStorage


try:
    import ZEO.ClientStorage
    ZEOSERVER = True
except:
    ZEOSERVER = False

try:
    from relstorage.options import Options
    from relstorage.storage import RelStorage
    RELSTORAGE = True
except ImportError:
    RELSTORAGE = False

try:
    import newt.db
    NEWT = True
except ImportError:
    NEWT = False


@configure.utility(provides=IDatabaseConfigurationFactory, name="ZODB")
def ZODBDatabaseConfigurationFactory(key, dbconfig):
    config = dbconfig.get('configuration', {})
    fs = ZODB.FileStorage.FileStorage(dbconfig['path'])
    db = DB(fs)
    try:
        rootobj = db.open().root()
        if not IDatabase.providedBy(rootobj):
            alsoProvides(rootobj, IDatabase)
        transaction.commit()
        rootobj = None
    except:
        pass
    finally:
        db.close()
    # Set request aware database for app
    db = RequestAwareDB(dbconfig['path'], **config)
    return Database(key, db)


@configure.utility(provides=IDatabaseConfigurationFactory, name="ZEO")
def ZEODatabaseConfigurationFactory(key, dbconfig):
    if not ZEOSERVER:
        raise Exception("You must install the ZEO package before you can use "
                        "it as a dabase adapter.")
    config = dbconfig.get('configuration', {})
    # Try to open it normal to create the root object
    address = (dbconfig['address'], dbconfig['port'])

    zeoconfig = dbconfig.get('zeoconfig', {})
    cs = ZEO.ClientStorage.ClientStorage(address, **zeoconfig)
    db = DB(cs)

    try:
        conn = db.open()
        rootobj = conn.root()
        if not IDatabase.providedBy(rootobj):
            alsoProvides(rootobj, IDatabase)
        transaction.commit()
    except:
        pass
    finally:
        rootobj = None
        conn.close()
        db.close()

    # Set request aware database for app
    cs = ZEO.ClientStorage.ClientStorage(address, **zeoconfig)
    db = RequestAwareDB(cs, **config)
    return Database(key, db)


@configure.utility(provides=IDatabaseConfigurationFactory, name="RELSTORAGE")
def RelStorageConfigurationFactory(key, dbconfig):
    if not RELSTORAGE:
        raise Exception("You must install the relstorage package before you can use "
                        "it as a dabase adapter.")
    config = dbconfig.get('configuration', {})
    options = Options(**dbconfig['options'])
    if dbconfig['type'] == 'postgres':
        from relstorage.adapters.postgresql import PostgreSQLAdapter
        dsn = "dbname={dbname} user={user} host={host} password={password} port={port}".format(**dbconfig['dsn'])  # noqa
        adapter = PostgreSQLAdapter(dsn=dsn, options=options)
    rs = RelStorage(adapter=adapter, options=options)
    db = DB(rs)
    try:
        conn = db.open()
        rootobj = conn.root()
        if not IDatabase.providedBy(rootobj):
            alsoProvides(rootobj, IDatabase)
        transaction.commit()
    except:
        pass
    finally:
        rootobj = None
        conn.close()
        db.close()
    rs = RelStorage(adapter=adapter, options=options)
    db = RequestAwareDB(rs, **config)
    return Database(key, db)


@configure.utility(provides=IDatabaseConfigurationFactory, name="NEWT")
def NewtConfigurationFactory(key, dbconfig):
    if not NEWT:
        raise Exception("You must install the newt.db package before you can use "
                        "it as a dabase adapter.")
    config = dbconfig.get('configuration', {})
    dsn = "dbname={dbname} user={username} host={host} password={password} port={port}".format(**dbconfig['dsn'])  # noqa
    adapter = newt.db.storage(dsn=dsn, **dbconfig['options'])
    db = newt.db.DB(dsn, **dbconfig['options'])
    try:
        conn = db.open()
        rootobj = conn.root()
        if not IDatabase.providedBy(rootobj):
            alsoProvides(rootobj, IDatabase)
        transaction.commit()
    except:
        pass
    finally:
        rootobj = None
        conn.close()
        db.close()
    adapter = newt.db.storage(dsn, **dbconfig['options'])
    db = newt.db._db.NewtDB(RequestAwareDB(adapter, **config))
    return Database(key, db)


@configure.utility(provides=IDatabaseConfigurationFactory, name="DEMO")
def DemoDatabaseConfigurationFactory(key, dbconfig):
    storage = DemoStorage(name=dbconfig['name'])
    db = DB(storage)
    alsoProvides(db.open().root(), IDatabase)
    transaction.commit()
    db.close()
    # Set request aware database for app
    db = RequestAwareDB(storage)
    return Database(key, db)
