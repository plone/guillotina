from guillotina import configure
from guillotina.db.db import GuillotinaDB
from guillotina.db.dummy import DummyStorage
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.factory.content import Database
from guillotina.interfaces import IDatabaseConfigurationFactory
from guillotina.utils import resolve_dotted_name


@configure.utility(provides=IDatabaseConfigurationFactory, name="postgresql")
async def DatabaseConfigurationFactory(key, dbconfig, app):
    config = dbconfig.get('configuration', {})
    dsn = "{scheme}://{user}:{password}@{host}:{port}/{dbname}".format(**dbconfig['dsn'])  # noqa
    partition_object = None
    if 'partition' in dbconfig:
        partition_object = resolve_dotted_name(dbconfig['partition'])
    pool_size = config.get('pool_size', 100)
    aps = PostgresqlStorage(dsn=dsn, partition=partition_object, name=key, pool_size=pool_size)
    if app is not None:
        await aps.initialize(loop=app.loop)
    else:
        await aps.initialize()
    dbc = {}
    dbc['database_name'] = key
    db = GuillotinaDB(aps, **dbc)
    await db.initialize()
    return Database(key, db)


@configure.utility(provides=IDatabaseConfigurationFactory, name="DUMMY")
async def DummyDatabaseConfigurationFactory(key, dbconfig, app):
    dss = DummyStorage()
    dbc = {}
    dbc['database_name'] = key
    db = GuillotinaDB(dss, **dbc)
    await db.initialize()
    return Database(key, db)
