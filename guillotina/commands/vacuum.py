from guillotina.commands import Command
from guillotina.utils import iter_databases
import logging


logger = logging.getLogger('guillotina')


class VacuumCommand(Command):
    description = 'Run vacuum on databases'

    async def vacuum(self, db):
        logger.warning(f'Starting vacuum on db: {db.id}')
        await db._storage.vacuum()
        logger.warning(f'Finished vacuum on db: {db.id}')

    async def run(self, arguments, settings, app):
        async for db in iter_databases():
            await self.vacuum(db)
