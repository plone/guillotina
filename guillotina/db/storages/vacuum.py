from guillotina import configure
from guillotina.const import TRASHED_ID
from guillotina.db.storages.utils import register_sql
from guillotina.db.interfaces import ICockroachStorage
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.interfaces import IVacuumProvider


register_sql('DELETE_TRASHED_OBJECTS', f"""
DELETE FROM {{table_name}}
WHERE zoid = ANY($1)
AND parent_id = '{TRASHED_ID}';
""")

register_sql('GET_BATCH_OF_TRASHED_OBJECTS', f"""
SELECT zoid from {{table_name}} where parent_id = '{TRASHED_ID}'
LIMIT $1;
""")

register_sql('TRASH_BATCH', f"""
WITH rows AS (
    UPDATE
        {{table_name}} t1
    SET
        parent_id = '{TRASHED_ID}'
    FROM (
            SELECT zoid
            FROM {{table_name}}
            WHERE parent_id = ANY($1)
            LIMIT $2
        ) as t2
    WHERE
        t1.zoid = t2.zoid
    RETURNING 1
)
SELECT count(*) FROM rows;
""")


@configure.adapter(for_=IPostgresStorage, provides=IVacuumProvider)
@configure.adapter(for_=ICockroachStorage, provides=IVacuumProvider)
class PGVacuum:

    def __init__(self, storage):
        self._storage = storage
        self._trashed = 0
        self._deleted = 0

    def status(self, terminate='\r', end=''):
        print(f"trashed: {self._trashed}, deleted: {self._deleted}{terminate}", end=end)

    async def __call__(self):
        '''
        - work with batches of trashed objects.
        - trash all children
        - do not delete object until all children have been reassigned as trashed
        '''
        storage = self._storage
        sql = self._storage._sql
        table_name = storage._objects_table_name
        async with storage.pool.acquire() as conn:
            while True:
                batch = await conn.fetch(
                    sql.get('GET_BATCH_OF_TRASHED_OBJECTS', table_name), 50)
                if len(batch) == 0:
                    break

                updated = 1
                while updated > 0:
                    result = await conn.fetch(
                        sql.get('TRASH_BATCH', table_name), [r['zoid'] for r in batch], 500)
                    updated = result[0]['count']
                    self._trashed += updated
                    self.status()

                await conn.execute(
                    sql.get(
                        'DELETE_TRASHED_OBJECTS', table_name), [r['zoid'] for r in batch])
                self._deleted += len(batch)
                self.status()
        self.status('', '\n')
