from guillotina import configure
from guillotina.const import TRASHED_ID
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.storages.utils import clear_table_name
from guillotina.interfaces import IMigration


async def _migrate_constraint(storage, conn):
    table_name = clear_table_name(storage._objects_table_name)
    result = await conn.fetch(
        """
SELECT * FROM pg_indexes
WHERE tablename = '{}' AND indexname = '{}_parent_id_id_key';
""".format(
            table_name, table_name
        )
    )
    if len(result) > 0:
        # check if we need to drop and create new constraint
        if TRASHED_ID not in result[0]["indexdef"]:  # pragma: no cover
            await conn.execute(
                """
ALTER TABLE {}
DROP CONSTRAINT {}_parent_id_id_key;
""".format(
                    storage._objects_table_name, table_name
                )
            )
            await conn.execute(
                storage._unique_constraints[0].format(
                    objects_table_name=storage._objects_table_name,
                    constraint_name=table_name,
                    TRASHED_ID=TRASHED_ID,
                )
            )


@configure.utility(name="4.2.7", provides=IMigration)
async def migrate_contraint(db, conn=None):
    storage = db.storage
    if not IPostgresStorage.providedBy(storage):
        return  # only for pg

    if conn is not None:
        await _migrate_constraint(storage, conn)
    else:
        async with storage.pool.acquire() as conn:
            await _migrate_constraint(storage, conn)
