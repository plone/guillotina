from guillotina import app_settings
from guillotina import migrate
from guillotina.content import create_content
from guillotina.interfaces import MIGRATION_DATA_REGISTRY_KEY
from guillotina.testing import GuillotinaFunctionalTestCase


class TestMigrations(GuillotinaFunctionalTestCase):

    def setUp(self):
        super(TestMigrations, self).setUp()

        self.login()

        # we want to control migrations defined in these tests...
        while len(migrate._migrations) > 0:
            migrate._migrations.pop()

        self.run_migrations = []

        def _add(app, version):

            def _migration_func(root):
                self.run_migrations.append((app, version))

            migrate._migrations.append(migrate.Migration(app, _migration_func, version))

        _add('foobar', '1.0')
        _add('foobar', '0.5')
        _add('foobar', '0.2')
        _add('foobar', '1.5.0')
        _add('foobarother', '1')
        _add('foobar', '2.1a1')
        _add('foobar', '1.0a1')
        _add('foobar', '1.0.1a1')
        _add('foobar', '1.0a9.dev0')

        app_settings['applications'] = ['foobar', 'foobarother']

    def test_get_migrations_for_application(self):
        self.assertEqual(len(migrate.get_migrations('foobar')), 8)

    def test_get_migrations_for_application_in_order(self):
        self.assertEqual(
            [m.to_version_raw for m in migrate.get_migrations('foobar')], [
                '0.2',
                '0.5',
                '1.0a1',
                '1.0a9.dev0',
                '1.0',
                '1.0.1a1',
                '1.5.0',
                '2.1a1'
            ])

    def test_get_migrations_from_version(self):
        self.assertEqual(
            [m.to_version_raw for m in migrate.get_migrations('foobar', '1.0')], [
                '1.0.1a1',
                '1.5.0',
                '2.1a1'
            ])

    def test_get_migrations_to_version(self):
        self.assertEqual(
            [m.to_version_raw for m in migrate.get_migrations('foobar', to_version='1.0')], [
                '0.2',
                '0.5',
                '1.0a1',
                '1.0a9.dev0',
                '1.0'
            ])

    def test_run_migrations(self):
        migrate.run_migrations(
            self.layer.app,
            migrate.get_migrations('foobar'))
        site = self.layer.portal
        registry = site['_registry']
        self.assertEqual(registry[MIGRATION_DATA_REGISTRY_KEY]['foobar'], '2.1a1')

    def test_should_only_get_migrations_for_activated_applications(self):
        self.assertEqual(len(migrate.get_migrations('foobar')), 8)
        app_settings['applications'] = []
        self.assertEqual(len(migrate.get_migrations('foobarother')), 0)
        self.assertEqual(len(migrate.get_migrations('foobar')), 0)
