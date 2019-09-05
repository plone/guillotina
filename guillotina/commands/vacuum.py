from guillotina.commands import Command
from guillotina.component import query_adapter
from guillotina.db.interfaces import IVacuumProvider
from guillotina.utils import iter_databases

import logging


logger = logging.getLogger("guillotina")


class VacuumCommand(Command):
    description = "Run vacuum on databases"

    async def vacuum(self, db):
        vacuumer = query_adapter(db._storage, IVacuumProvider)
        if vacuumer is None:
            logger.warning(f"No vacuum provider found for storage: {db._storage}")
            return
        logger.warning(f"Starting vacuum on db: {db.id}")
        await vacuumer()
        logger.warning(f"Finished vacuum on db: {db.id}")

    async def run(self, arguments, settings, app):
        async for db in iter_databases():
            try:
                await self.vacuum(db)
            except Exception:  # pragma: no cover
                logger.error("Error vacuuming db", exc_info=True)
