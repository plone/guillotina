from guillotina import configure
from guillotina.db import etcd
from guillotina.db.interfaces import ILockingStrategy
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.none import TIDOnlyStrategy
from guillotina.exceptions import ConflictError

import asyncio
import logging
import time


logger = logging.getLogger('guillotina')


@configure.adapter(
    for_=(IStorage, ITransaction),
    provides=ILockingStrategy, name="lock")
class LockStrategy(TIDOnlyStrategy):
    '''
    *this strategy relies on using etcd for locking*

    A transaction strategy that depends on locking objects in order to safely
    write to them.

    Application logic needs to implement the object locking.

    Unlocking should be done in the tpc_finish phase.
    '''

    def __init__(self, storage, transaction):
        self._storage = storage
        self._transaction = transaction

        options = storage._options
        self._lock_ttl = options.get('lock_ttl', 10)
        etcd_options = options.get('etcd', {})
        self._etcd_base_key = etcd_options.pop('base_key', 'guillotina-')
        self._etcd_acquire_timeout = etcd_options.pop('acquire_timeout', 3)

        if not hasattr(self._storage, '_etcd_client'):
            self._storage._etcd_client = etcd.Client(**etcd_options)
        self._etcd_client = self._storage._etcd_client

    async def tpc_vote(self):
        """
        Never a problem for voting since we're relying on locking
        """
        return True

    async def tpc_finish(self):
        if not self.writable_transaction:
            return

        for ob in self._transaction.modified.values():
            if ob.__locked__:
                await self.unlock(ob)

    def _get_key(self, ob):
        return '{}-{}-lock'.format(self._etcd_base_key, ob._p_oid)

    async def _wait_for_lock(self, key, wait_index=None):
        '''
        We should probably think of rewriting with wait=true instead of retrying
        '''
        # this method *should* use the wait_for with a timeout
        if wait_index is None:
            result = await self._etcd_client.get(key)
        else:
            logger.info(f'etcd waiting for {key}, index {wait_index}')
            start = time.time()
            result = await self._etcd_client.get(key, wait='true',
                                                 waitIndex=wait_index + 1)
            logger.info(f'etcd got change after wait {key}, index {wait_index}, '
                        f'in {time.time() - start}')
        if 'node' in result:
            if result['node']['value'] == 'locked':
                return await self._wait_for_lock(
                    key, wait_index=result['node']['modifiedIndex'])
            else:
                set_result = await self._etcd_client.set(
                    key, 'locked', ttl=self._lock_ttl,
                    prevIndex=result['node']['modifiedIndex'])
                if 'errorCode' in set_result:
                    return await self._wait_for_lock(key, wait_index=set_result['index'])
                else:
                    logger.info(f"got lock for existing {key}, index {result['node']['modifiedIndex']}, "
                                f"wait index: {wait_index}")
                    return set_result
        else:
            set_result = await self._etcd_client.set(
                key, 'locked', ttl=self._lock_ttl,
                prevExist='false')
            if 'errorCode' in set_result:
                return await self._wait_for_lock(key, wait_index=set_result['index'])
            else:
                return set_result

    async def lock(self, obj):
        assert not obj.__new_marker__  # should be modifying an object
        if obj.__locked__:  # we've already locked this...
            return

        obj.__locked__ = True
        if obj._p_oid not in self._transaction.modified:
            # need to added it when locking...
            self._transaction.modified[obj._p_oid] = obj
        key = self._get_key(obj)

        try:
            await asyncio.wait_for(
                self._wait_for_lock(key),
                timeout=self._etcd_acquire_timeout)
        except asyncio.TimeoutError:
            raise ConflictError('Could not lock ob for writing')

    async def unlock(self, obj):
        if not obj.__locked__:
            # already unlocked
            return
        obj.__locked__ = False
        key = self._get_key(obj)
        await self._etcd_client.set(key, 'unlocked', ttl=self._lock_ttl)
