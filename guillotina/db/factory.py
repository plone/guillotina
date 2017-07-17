from guillotina import configure
from guillotina.db.db import GuillotinaDB
from guillotina.db.storages.cockroach import CockroachStorage
from guillotina.db.storages.dummy import DummyStorage
from guillotina.db.storages.pg import PostgresqlStorage
from guillotina.factory.content import Database
from guillotina.interfaces import IDatabaseConfigurationFactory
from guillotina.utils import resolve_dotted_name


async def _PGConfigurationFactory(key, dbconfig, app,
                                  storage_factory=PostgresqlStorage):
    # b/w compat, we don't use this for storage options anymore
    config = dbconfig.get('configuration', {})

    if isinstance(dbconfig['dsn'], str):
        dsn = dbconfig['dsn']
    else:
        dsn = "{scheme}://{user}:{password}@{host}:{port}/{dbname}".format(
            **dbconfig['dsn'])

    partition_object = None
    if 'partition' in dbconfig:
        partition_object = resolve_dotted_name(dbconfig['partition'])

    dbconfig.update({
        'dsn': dsn,
        'name': key,
        'partition': partition_object,
        'pool_size': dbconfig.get('pool_size', config.get('pool_size', 13))
    })

    connection_options = {}
    if 'ssl' in dbconfig:
        import ssl
        ssl_config = dbconfig['ssl']
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        ssl_context.load_verify_locations(ssl_config['ca'])
        ssl_context.load_cert_chain(ssl_config['cert'], keyfile=ssl_config['key'])
        connection_options['ssl'] = ssl_context

    aps = storage_factory(**dbconfig)
    if app is not None:
        await aps.initialize(loop=app.loop, **connection_options)
    else:
        await aps.initialize(**connection_options)
    dbc = {}
    dbc['database_name'] = key
    db = GuillotinaDB(aps, **dbc)
    await db.initialize()
    return Database(key, db)


@configure.utility(provides=IDatabaseConfigurationFactory, name="postgresql")
async def PGDatabaseConfigurationFactory(key, dbconfig, app):
    return await _PGConfigurationFactory(key, dbconfig, app)


@configure.utility(provides=IDatabaseConfigurationFactory, name="cockroach")
async def CRDatabaseConfigurationFactory(key, dbconfig, app):
    return await _PGConfigurationFactory(key, dbconfig, app,
                                         storage_factory=CockroachStorage)


@configure.utility(provides=IDatabaseConfigurationFactory, name="DUMMY")
async def DummyDatabaseConfigurationFactory(key, dbconfig, app):
    dss = DummyStorage()
    dbc = {}
    dbc['database_name'] = key
    db = GuillotinaDB(dss, **dbc)
    await db.initialize()
    return Database(key, db)
