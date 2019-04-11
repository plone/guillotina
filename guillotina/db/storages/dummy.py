from guillotina.const import ROOT_ID
from guillotina.db.interfaces import IStorage
from guillotina.db.storages.base import BaseStorage
from guillotina.exceptions import ConflictIdOnContainer
from zope.interface import implementer

import asyncio
import logging
import os
import pickle


logger = logging.getLogger('guillotina')


@implementer(IStorage)
class DummyStorage(BaseStorage):
    """
    Dummy in-memory storage for testing
    """

    _last_transaction = 1
    _transaction_strategy = 'resolve'
    _supports_unique_constraints = True

    _db = None

    def __init__(self, read_only=False):
        self._lock = asyncio.Lock()
        self._db = {}
        self._blobs = {}
        super().__init__(read_only)

    async def finalize(self):
        pass

    async def initialize(self, loop=None):
        pass

    async def remove(self):
        """Reset the tables"""
        pass

    async def open(self):
        return self

    async def close(self, con):
        pass

    async def root(self):
        return await self.load(None, ROOT_ID)

    async def last_transaction(self, txn):
        return self._last_transaction

    async def get_next_tid(self, txn):
        async with self._lock:
            self._last_transaction += 1
            return self._last_transaction

    async def load(self, txn, oid):
        objects = self._db[oid]
        if objects is None:
            raise KeyError(oid)
        return objects

    async def start_transaction(self, txn):
        pass

    def get_txn(self, txn):
        if not getattr(txn, '_db_txn', None):
            txn._db_txn = {
                'added': {},
                'removed': []
            }
        return txn._db_txn

    async def store(self, oid, old_serial, writer, obj, txn):
        assert oid is not None
        p = writer.serialize()  # This calls __getstate__ of obj
        json = await writer.get_json()
        part = writer.part
        if part is None:
            part = 0
        existing = self._db.get(oid, {})
        if obj.__new_marker__ and writer.parent_id in self._db:
            # look in all the children for object of same id
            parent = self._db[writer.parent_id]
            if writer.id in parent['children']:
                raise ConflictIdOnContainer(Exception('Duplicate id'))

        tobj = {
            'zoid': oid,
            'tid': txn._tid,
            'size': len(p),
            'part': part,
            'resource': writer.resource,
            'of': writer.of,
            'serial': old_serial,
            'parent_id': writer.parent_id,
            'id': writer.id,
            'type': writer.type,
            'json': json,
            'state': p,
            'children': existing.get('children', {}),
            'ofs': existing.get('ofs', {})
        }
        self.get_txn(txn)['added'][oid] = tobj
        return txn._tid, len(p)

    async def delete(self, txn, oid):
        self.get_txn(txn)['removed'].append(oid)

    async def commit(self, transaction):
        for oid, element in self.get_txn(transaction)['added'].items():
            if oid in self._db and self._db[oid]['parent_id'] != element['parent_id']:
                # can move object move, we need to cleanup here...
                old_parent_ob = self._db[self._db[oid]['parent_id']]
                children = {v: k for k, v in old_parent_ob['children'].items()}
                if oid in children:
                    del old_parent_ob['children'][children[oid]]

            self._db[oid] = element
            if element['parent_id'] in self._db:
                children = {v: k for k, v in self._db[element['parent_id']]['children'].items()}
                if oid in children:
                    # clear in case of object rename
                    del self._db[element['parent_id']]['children'][children[oid]]
                self._db[element['parent_id']]['children'][element['id']] = oid
            if element['of'] and element['of'] in self._db:
                self._db[element['of']]['ofs'][element['id']] = oid

        for oid in self.get_txn(transaction)['removed']:
            tobj = self._db[oid]
            del self._db[oid]
            if tobj['parent_id'] and tobj['parent_id'] in self._db:
                parent_ob = self._db[tobj['parent_id']]
                children = {v: k for k, v in parent_ob['children'].items()}
                if oid in children:
                    del parent_ob['children'][children[oid]]
            if tobj['of'] and tobj['of'] in self._db:
                of_ob = self._db[tobj['of']]
                ofs = {v: k for k, v in of_ob['ofs'].items()}
                if oid in ofs:
                    del of_ob['ofs'][ofs[oid]]

        return transaction._tid

    async def abort(self, transaction):
        transaction._db_txn = None

    # Introspection

    async def keys(self, txn, oid):
        keys = []
        if oid not in self._db:
            return []
        for cid, coid in self._db[oid]['children'].items():
            obj = await self.load(txn, coid)
            keys.append(obj)
        return keys

    async def get_child(self, txn, parent_id, id):
        parent_ob = self._db[parent_id]
        return await self.load(txn, parent_ob['children'][id])

    async def has_key(self, txn, parent_id, id):
        if parent_id in self._db:
            parent_ob = self._db[parent_id]
            return id in parent_ob['children']

    async def len(self, txn, oid):
        if oid in self._db:
            return len(self._db[oid]['children'])
        return 0

    async def items(self, txn, oid):  # pragma: no cover
        for cid, coid in self._db[oid]['children'].items():
            obj = await self.load(txn, coid)
            yield obj

    async def get_children(self, txn, parent, keys):
        children = []
        for cid, coid in self._db[parent]['children'].items():
            if cid not in keys:
                continue
            record = await self.load(txn, coid)
            children.append(record)
        return children

    async def get_annotation(self, txn, oid, id):
        return await self.load(txn, self._db[oid]['ofs'][id])

    async def get_annotation_keys(self, txn, oid):
        keys = []
        for of_id in self._db[oid]['ofs'].values():
            obj = await self.load(txn, of_id)
            keys.append(obj)
        return keys

    async def del_blob(self, txn, bid):
        if bid in self._blobs:
            del self._blobs[bid]

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        if bid not in self._blobs:
            self._blobs[bid] = {
                'oid': oid,
                'chunks': []
            }
        self._blobs[bid]['chunks'].append(data)

    async def read_blob_chunk(self, txn, bid, chunk=0):
        return {
            'data': self._blobs[bid]['chunks'][chunk]
        }

    async def get_conflicts(self, txn):
        return []

    async def get_page_of_keys(self, txn, oid, page=1, page_size=1000):
        children = self._db[oid]['children']
        keys = [k for k in sorted(children.values())]
        start = (page - 1) * page_size
        end = start + page_size
        return [self._db[key]['id'] for key in keys[start:end]]

    async def vacuum(self):
        '''
        nothing to vacuum in this implementation
        '''


@implementer(IStorage)
class DummyFileStorage(DummyStorage):  # pragma: no cover

    def __init__(self, filename='g.db'):
        super(DummyFileStorage, self).__init__()
        self.filename = filename
        self.blob_filename = self.filename + '.blobs'
        self.__load()

    def __load(self):
        if not os.path.exists(self.filename):
            return
        with open(self.filename, 'rb') as fi:
            try:
                self._db = pickle.loads(fi.read())
            except EOFError:
                logger.warning(f'Could not load db file {self.filename}')
        if os.path.exists(self.blob_filename):
            with open(self.blob_filename, 'rb') as fi:
                try:
                    self._blobs = pickle.loads(fi.read())
                except EOFError:
                    logger.warning(f'Could not load db file {self.blob_filename}')

    def __save(self):
        with open(self.filename, 'wb') as fi:
            fi.write(pickle.dumps(self._db))
        with open(self.blob_filename, 'wb') as fi:
            fi.write(pickle.dumps(self._blobs))

    async def commit(self, transaction):
        await super().commit(transaction)
        self.__save()
