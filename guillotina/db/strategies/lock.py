from guillotina import configure
from guillotina.db import etcd
from guillotina.db.interfaces import ILockingStrategy
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.none import TIDOnlyStrategy
from guillotina.exceptions import ConflictError

import asyncio
import logging


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

    async def _wait_for_lock(self, key, retries=0):
        '''
        We do not use *wait* syntax for getting lock because, oddly, it's much
        more slow than just trying a write and retrying a few times before giving up.

        Yes, MUCH slower.
        '''
        # this method *should* use the wait_for with a timeout
        if retries > 5:
            raise ConflictError('Could not lock ob for writing')

        result = await self._etcd_client.set(
            key, 'locked', ttl=self._lock_ttl, prevExist=False)
        if 'errorCode' in result:
            await asyncio.sleep(0.05)
            return self._wait_for_lock(key, retries=retries + 1)

        if retries > 0:
            print('got it after retry')
        return result

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
            await asyncio.wait_for(self._wait_for_lock(key),
                                   timeout=self._etcd_acquire_timeout)
        except asyncio.TimeoutError:
            raise ConflictError('Could not lock ob for writing')

    async def unlock(self, obj):
        if not obj.__locked__:
            # already unlocked
            return
        obj.__locked__ = False
        key = self._get_key(obj)
        await self._etcd_client.delete(key, 'unlocked', ttl=self._lock_ttl)
