from plone.server import app_settings
from plone.server import migrate
from plone.server.commands import Command
from plone.server.interfaces import IDatabase
from plone.server.testing import TESTING_SETTINGS
from zope.component import getUtility
from plone.server.interfaces import IApplication


def traverse_to_path(app, path):
    parts = path.split('/')[1:]
    db_id = parts[0]
    ob = db = app[db_id]
    for part in parts[1:]:
        ob = ob[part]
    return db, ob


class MigrateCommand(Command):
    description = 'Plone server migration utility'

    def get_parser(self):
        parser = super(MigrateCommand, self).get_parser()
        parser.add_argument('-d', '--dry-run', action='store_true',
                            dest='dry_run', help='Dry run')
        parser.add_argument('-s', '--site',
                            help='Specific site to run migration against')
        parser.add_argument('-r', '--report', action='store_true',
                            help='Report only on current state')
        parser.add_argument('-a', '--app',
                            help='Run migrations only for particular application')
        parser.add_argument('-v', '--to-version',
                            dest='to_version',
                            help='Migrate to a specific version')
        return parser

    def report(self, arguments, sites, apps):
        for site_path, data in sites.items():
            db, site = data
            registry = site['_registry']
            try:
                installed_versions = registry['_migrations_info']
            except KeyError:
                installed_versions = {}
            title = '{} Migrations'.format(site_path)
            print('\n\n')
            print(title)
            print('=' * len(title))
            print('{0:<20}{1:<40}{2:<60}'.format(
                'application',
                'installed',
                'available'
            ))
            print('{0:<20}{1:<40}{2:<60}'.format(
                '-' * len('application'),
                '-' * len('installed'),
                '-' * len('available')
            ))
            for app in apps:
                _migrations = migrate.get_migrations(
                    app, to_version=arguments.to_version,
                    from_version=installed_versions.get(app))
                version = upgrade_to = None
                if len(_migrations) > 0:
                    upgrade_to = _migrations[-1].to_version_raw
                if app in installed_versions:
                    version = installed_versions[app]
                if version or upgrade_to:
                    items = [app]
                    if version:
                        items.append(version)
                    else:
                        items.append('-')
                    if upgrade_to:
                        items.append('{}({} migrations)'.format(
                            upgrade_to,
                            len(_migrations)
                        ))
                    else:
                        items.append('-')
                    print('{0:<20}{1:<40}{2:<60}'.format(*items))

    def run(self, arguments, settings, app):
        app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']

        root = getUtility(IApplication, name='root')

        # get sites to run command against
        if arguments.site:
            sites = {
                arguments.site: traverse_to_path(app, arguments.site)
            }
        else:
            sites = {}
            for _id, db in root:
                if IDatabase.providedBy(db):
                    for s_id in db.keys():
                        sites['/' + _id + '/' + s_id] = (db, db[s_id])

        if len(sites) == 0:
            print('No sites found')

        if arguments.app:
            apps = [arguments.app]
        else:
            apps = migrate.get_migratable_applications()

        if not arguments.report:
            # run them...
            for db, site in sites.values():
                for app in apps:
                    registry = site['_registry']
                    try:
                        installed_versions = registry['_migrations_info']
                    except KeyError:
                        installed_versions = {}
                    _migrations = migrate.get_migrations(
                        app, to_version=arguments.to_version,
                        from_version=installed_versions.get(app))
                    if len(_migrations) > 0:
                        if not arguments.dry_run and not arguments.report:
                            db.tm_.begin()
                        migrate.run_site_migrations(site, _migrations, db)
                        if not arguments.dry_run and not arguments.report:
                            db.tm_.commit()

        self.report(arguments, sites, apps)
