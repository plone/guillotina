import logging
from distutils.version import StrictVersion

from guillotina.commands import Command
from guillotina.component import get_utilities_for
from guillotina.interfaces import IMigration
from guillotina.transactions import managed_transaction
from guillotina.utils import iter_databases


logger = logging.getLogger('guillotina')


class MigrateCommand(Command):
    description = 'Run migrate on databases'

    async def migrate(self, db):
        migrations = sorted(
            get_utilities_for(IMigration))
        self.request._tm = db.get_transaction_manager()
        async with managed_transaction(self.request, write=True) as txn:
            # make sure to get fresh copy
            txn._manager._hard_cache.clear()
            root = await db.get_root()
            current_version = StrictVersion(root.migration_version)
            for version, migration in migrations:
                if StrictVersion(version) > current_version:
                    logger.warning(f'Starting migration on db {version}: {db.id}')
                    await migration(db)
                    logger.warning(f'Finished migration on db {version}: {db.id}')
                    root.migration_version = version
            txn.register(root)

    async def run(self, arguments, settings, app):
        async for db in iter_databases():
            await self.migrate(db)
