from guillotina import configure
from guillotina.const import TRASHED_ID
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.storages.utils import clear_table_name
from guillotina.interfaces import IMigration


@configure.utility(
    name='4.2.7',
    provides=IMigration)
async def migrate_contraint(db):
    storage = db.storage
    if not IPostgresStorage.providedBy(storage):
        return  # only for pg

    table_name = clear_table_name(storage._objects_table_name)
    result = await storage.read_conn.fetch('''
SELECT * FROM pg_indexes
WHERE tablename = '{}' AND indexname = '{}_parent_id_id_key';
'''.format(table_name, table_name))
    if len(result) > 0:
        # check if we need to drop and create new constraint
        if TRASHED_ID not in result[0]['indexdef']:
            await storage.read_conn.execute('''
ALTER TABLE {}
DROP CONSTRAINT {}_parent_id_id_key;
'''.format(storage._objects_table_name, table_name))
            await storage.read_conn.execute(storage._unique_constraint.format(
                objects_table_name=storage._objects_table_name,
                constraint_name=table_name,
                TRASHED_ID=TRASHED_ID
            ))
