from distutils.version import StrictVersion
from guillotina.commands import Command
from guillotina.component import get_utilities_for
from guillotina.interfaces import IMigration
from guillotina.transactions import transaction
from guillotina.utils import iter_databases

import logging


logger = logging.getLogger("guillotina")


class MigrateCommand(Command):
    description = "Run migrate on databases"

    async def migrate(self, db):
        migrations = sorted(get_utilities_for(IMigration), key=lambda v: StrictVersion(v[0]))
        async with transaction(db=db) as txn:
            # make sure to get fresh copy
            txn._manager._hard_cache.clear()
            root = await db.get_root()
            current_version = StrictVersion(root.migration_version)
            for version, migration in migrations:
                if StrictVersion(version) > current_version:
                    logger.warning(f"Starting migration on db {version}: {db.id}")
                    await migration(db)
                    logger.warning(f"Finished migration on db {version}: {db.id}")
                    root.migration_version = version
            txn.register(root)

    async def run(self, arguments, settings, app):
        async for db in iter_databases():
            await self.migrate(db)
