from guillotina.db import ROOT_ID
from guillotina.db.interfaces import IStorage
from guillotina.db.storages.base import BaseStorage
from guillotina.exceptions import ConflictIdOnContainer
from zope.interface import implementer

import asyncio
import os
import pickle


@implementer(IStorage)
class DummyStorage(BaseStorage):
    """
    Dummy in-memory storage for testing
    """

    _last_transaction = 1
    _transaction_strategy = 'resolve'

    __db = None

    def __init__(self, read_only=False):
        self._lock = asyncio.Lock()
        self.__db = {}
        self.__blobs = {}
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
        objects = self.__db[oid]
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
        existing = self.__db.get(oid, {})
        if obj.__new_marker__ and writer.parent_id in self.__db:
            # look in all the children for object of same id
            parent = self.__db[writer.parent_id]
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
            if oid in self.__db and self.__db[oid]['parent_id'] != element['parent_id']:
                # can move object move, we need to cleanup here...
                old_parent_ob = self.__db[self.__db[oid]['parent_id']]
                children = {v: k for k, v in old_parent_ob['children'].items()}
                if oid in children:
                    del old_parent_ob['children'][children[oid]]

            self.__db[oid] = element
            if element['parent_id'] in self.__db:
                children = {v: k for k, v in self.__db[element['parent_id']]['children'].items()}
                if oid in children:
                    # clear in case of object rename
                    del self.__db[element['parent_id']]['children'][children[oid]]
                self.__db[element['parent_id']]['children'][element['id']] = oid
            if element['of'] and element['of'] in self.__db:
                self.__db[element['of']]['ofs'][element['id']] = oid

        for oid in self.get_txn(transaction)['removed']:
            tobj = self.__db[oid]
            del self.__db[oid]
            if tobj['parent_id'] and tobj['parent_id'] in self.__db:
                parent_ob = self.__db[tobj['parent_id']]
                children = {v: k for k, v in parent_ob['children'].items()}
                if oid in children:
                    del parent_ob['children'][children[oid]]
            if tobj['of'] and tobj['of'] in self.__db:
                of_ob = self.__db[tobj['of']]
                ofs = {v: k for k, v in of_ob['ofs'].items()}
                if oid in ofs:
                    del of_ob['ofs'][ofs[oid]]

        return transaction._tid

    async def abort(self, transaction):
        transaction._db_txn = None

    # Introspection

    async def keys(self, txn, oid):
        keys = []
        if oid not in self.__db:
            return []
        for cid, coid in self.__db[oid]['children'].items():
            obj = await self.load(txn, coid)
            keys.append(obj)
        return keys

    async def get_child(self, txn, parent_id, id):
        parent_ob = self.__db[parent_id]
        return await self.load(txn, parent_ob['children'][id])

    async def has_key(self, txn, parent_id, id):
        if parent_id in self.__db:
            parent_ob = self.__db[parent_id]
            return id in parent_ob['children']

    async def len(self, txn, oid):
        if oid in self.__db:
            return len(self.__db[oid]['children'])
        return 0

    async def items(self, txn, oid):  # pragma: no cover
        for cid, coid in self.__db[oid]['children'].items():
            obj = await self.load(txn, coid)
            yield obj

    async def get_children(self, txn, parent, keys):
        children = []
        for cid, coid in self.__db[parent]['children'].items():
            if cid not in keys:
                continue
            record = await self.load(txn, coid)
            children.append(record)
        return children

    async def get_annotation(self, txn, oid, id):
        return await self.load(txn, self.__db[oid]['ofs'][id])

    async def get_annotation_keys(self, txn, oid):
        keys = []
        for of_id in self.__db[oid]['ofs'].values():
            obj = await self.load(txn, of_id)
            keys.append(obj)
        return keys

    async def del_blob(self, txn, bid):
        if bid in self.__blobs:
            del self.__blobs[bid]

    async def write_blob_chunk(self, txn, bid, oid, chunk_index, data):
        if bid not in self.__blobs:
            self.__blobs[bid] = {
                'oid': oid,
                'chunks': []
            }
        self.__blobs[bid]['chunks'].append(data)

    async def read_blob_chunk(self, txn, bid, chunk=0):
        return {
            'data': self.__blobs[bid]['chunks'][chunk]
        }

    async def get_conflicts(self, txn):
        return []

    async def get_page_of_keys(self, txn, oid, page=1, page_size=1000):
        children = self.__db[oid]['children']
        keys = [k for k in sorted(children.values())]
        start = (page - 1) * page_size
        end = start + page_size
        return [self.__db[key]['id'] for key in keys[start:end]]


@implementer(IStorage)
class DummyFileStorage(DummyStorage):  # pragma: no cover

    def __init__(self, filename='g.db'):
        super(DummyFileStorage, self).__init__()
        self.filename = filename
        self.__load()

    def __load(self):
        if not os.path.exists(self.filename):
            return
        with open(self.filename, 'rb') as fi:
            self.__db = pickle.loads(fi.read())

    def __save(self):
        with open(self.filename, 'wb') as fi:
            fi.write(pickle.dumps(self.__db))

    async def commit(self, transaction):
        await super().commit(transaction)
        self.__save()
