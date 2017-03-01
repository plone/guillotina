from persistent.dict import PersistentDict
from pkg_resources import parse_version
from guillotina import logger
from guillotina.interfaces import MIGRATION_DATA_REGISTRY_KEY


_migrations = []


class Migration(object):

    def __init__(self, application, func, to_version=None):
        self.application = application
        self.func = func
        self.to_version = parse_version(to_version)
        self.to_version_raw = to_version

    def __cmp__(self, other):
        return self.to_version > other.to_version

    def __gt__(self, other):
        return self.to_version > other.to_version


def migration(application, to_version=None):
    def _func(func):
        _migrations.append(Migration(application, func, to_version))
    return _func


def get_migratable_applications():
    from guillotina import app_settings
    apps = []
    applications = app_settings['applications'] + ['guillotina']
    for migration in _migrations:
        if migration.application not in apps and migration.application in applications:
            apps.append(migration.application)
    return apps


def get_migrations(application, from_version=None, to_version=None):
    from guillotina import app_settings

    if from_version:
        from_version = parse_version(from_version)
    if to_version:
        to_version = parse_version(to_version)

    applications = app_settings['applications'] + ['guillotina']
    migrations = []
    for migration in _migrations:
        if migration.application != application or migration.application not in applications:
            continue
        if from_version and migration.to_version <= from_version:
            continue
        if to_version and migration.to_version > to_version:
            continue
        if migration.application not in applications:
            continue
        migrations.append(migration)

    migrations.sort()
    return migrations


def run_site_migrations(site, migrations, db=None):
    # prevent circular imports...

    site_name = site.id
    if db:
        site_name = '/{}/{}'.format(db.id, site_name)
    for migration in migrations:
        logger.info('Running migration for "{}" to version "{}" on site "{}"'.format(
            migration.application,
            migration.to_version.public,
            site_name
        ))
        try:
            migration.func(site)
        except:
            logger.info('Error running migration for "{}" to version "{}" on site "{}"'.format(
                migration.application,
                migration.to_version.public,
                site_name
            ), exc_info=True)
            raise

        registry = site['_registry']
        if MIGRATION_DATA_REGISTRY_KEY not in registry:
            registry[MIGRATION_DATA_REGISTRY_KEY] = PersistentDict()
        registry[MIGRATION_DATA_REGISTRY_KEY][migration.application] = migration.to_version_raw


def run_migrations(root, migrations):
    # prevent circular imports...
    from guillotina.interfaces import IDatabase
    sites = []
    for _id, db in root:
        if IDatabase.providedBy(db):
            sites.extend([db[s_id] for s_id in db.keys()])

    for site in sites:
        run_site_migrations(site, migrations)
