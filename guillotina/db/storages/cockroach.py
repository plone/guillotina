from guillotina.db.storages import pg


INSERT = """
    INSERT INTO objects
    (zoid, tid, state_size, part, resource, of, otid, parent_id, id, type, state)
    VALUES ($1::varchar(32), $2::int, $3::int, $4::int, $5::boolean, $6::varchar(32), $7::int,
            $8::varchar(32), $9::text, $10::text, $11::bytea)
    ON CONFLICT (zoid)
    DO UPDATE SET
        tid = EXCLUDED.tid,
        state_size = EXCLUDED.state_size,
        part = EXCLUDED.part,
        resource = EXCLUDED.resource,
        of = EXCLUDED.of,
        otid = EXCLUDED.otid,
        parent_id = EXCLUDED.parent_id,
        id = EXCLUDED.id,
        type = EXCLUDED.type,
        state = EXCLUDED.state;
    """


NEXT_TID = """SELECT unique_rowid()"""
MAX_TID = "SELECT COALESCE(MAX(tid), 0) from objects;"


class CockroachStorage(pg.PostgresqlStorage):
    '''
    Differences that we use from postgresql:
        - no jsonb support
        - no CASCADE support(ON DELETE CASCADE)
            - used by objects and blobs tables
            - right now, deleting will potentially leave dangling rows around
            - potential solutions
                - utility to recursively delete?
                - complex delete from query that does the sub queries to delete?
        - no sequence support
            - use serial construct of unique_rowid() instead
    '''

    _object_schema = pg.PostgresqlStorage._object_schema.copy()
    del _object_schema['json']  # no json db support
    _object_schema.update({
        'of': 'VARCHAR(32) REFERENCES objects',
        'parent_id': 'VARCHAR(32) REFERENCES objects',  # parent oid
    })

    _blob_schema = pg.PostgresqlStorage._blob_schema.copy()
    _blob_schema.update({
        'zoid': 'VARCHAR(32) NOT NULL REFERENCES objects',
    })

    _initialize_statements = [
        'CREATE INDEX IF NOT EXISTS object_tid ON objects (tid);',
        'CREATE INDEX IF NOT EXISTS object_of ON objects (of);',
        'CREATE INDEX IF NOT EXISTS object_part ON objects (part);',
        'CREATE INDEX IF NOT EXISTS object_parent ON objects (parent_id);',
        'CREATE INDEX IF NOT EXISTS object_id ON objects (id);',
        'CREATE INDEX IF NOT EXISTS blob_bid ON blobs (bid);',
        'CREATE INDEX IF NOT EXISTS blob_zoid ON blobs (zoid);',
        'CREATE INDEX IF NOT EXISTS blob_chunk ON blobs (chunk_index);'
    ]

    async def initialize_tid_statements(self):
        self._stmt_next_tid = await self._read_conn.prepare(NEXT_TID)
        self._stmt_max_tid = await self._read_conn.prepare(MAX_TID)

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None

        smt = await self._get_prepared_statement(txn, 'insert', INSERT)

        p = writer.serialize()  # This calls __getstate__ of obj
        if len(p) >= self._large_record_size:
            self._log.warn("Too long object %d" % (obj.__class__, len(p)))
        part = writer.part
        if part is None:
            part = 0
        # (zoid, tid, state_size, part, main, parent_id, type, json, state)
        await smt.fetchval(
            oid,                 # The OID of the object
            txn._tid,            # Our TID
            len(p),              # Len of the object
            part,                # Partition indicator
            writer.resource,     # Is a resource ?
            writer.of,           # It belogs to a main
            old_serial,          # Old serial
            writer.parent_id,    # Parent OID
            writer.id,           # Traversal ID
            writer.type,         # Guillotina type
            p                    # Pickle state
        )
        obj._p_estimated_size = len(p)
        return txn._tid, len(p)
