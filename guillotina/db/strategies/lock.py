from aiohttp.client_exceptions import ClientConnectionError
from aiohttp.client_exceptions import ClientResponseError
from aiohttp.web_exceptions import HTTPException
from guillotina import configure
from guillotina.db.interfaces import ILockingStrategy
from guillotina.db.interfaces import IStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.strategies.none import TIDOnlyStrategy
from guillotina.db.transaction import Status
from guillotina.exceptions import ConflictError

import aio_etcd
import aiohttp
import asyncio
import logging
import socket
import time


logger = logging.getLogger('guillotina')


class ETCDClient(aio_etcd.Client):

    async def api_execute(self, path, method, params=None):
        """ Executes the query. """

        if not path.startswith('/'):
            raise ValueError('Path does not start with /')

        url = self._base_uri + path

        async with aiohttp.ClientSession(loop=self._loop) as session:
            some_request_failed = False
            response = False

            if not path.startswith('/'):
                raise ValueError('Path does not start with /')

            if not self._machines_available:
                await self._update_machines()

            while not response:
                try:
                    response = await session.request(
                        method,
                        url,
                        params=params,
                        auth=self._get_auth(),
                        allow_redirects=self.allow_redirect)
                    # Check the cluster ID hasn't changed under us.  We use
                    # preload_content=False above so we can read the headers
                    # before we wait for the content of a watch.
                    self._check_cluster_id(response)
                    # Now force the data to be preloaded in order to trigger any
                    # IO-related errors in this method rather than when we try to
                    # access it later.
                    _ = await response.read()  # noqa
                    # urllib3 doesn't wrap all httplib exceptions and earlier versions
                    # don't wrap socket errors either.
                except (ClientConnectionError, ClientResponseError,
                        HTTPException, socket.error) as e:
                    logger.error("Request to server %s failed: %r",
                                 self._base_uri, e)
                    if self._allow_reconnect:
                        logger.info("Reconnection allowed, looking for another "
                                    "server.")
                        # _next_server() raises EtcdException if there are no
                        # machines left to try, breaking out of the loop.
                        self._base_uri = self._next_server(cause=e)
                        some_request_failed = True

                        # if exception is raised on _ = response.data
                        # the condition for while loop will be False
                        # but we should retry
                        response = False
                    else:
                        logger.debug("Reconnection disabled, giving up.")
                        raise aio_etcd.EtcdConnectionFailed(
                            "Connection to etcd failed due to %r" % e,
                            cause=e
                        )
                except aio_etcd.EtcdClusterIdChanged as e:
                    logger.warning(e)
                    raise
                except asyncio.CancelledError:
                    # don't complain
                    raise
                except Exception:
                    logger.exception("Unexpected request failure, re-raising.")
                    raise
                else:
                    try:
                        response = await self._handle_server_response(response)
                    except aio_etcd.EtcdException as e:
                        if "during rolling upgrades" in e.payload['message']:
                            response = False
                            some_request_failed = True
                        else:
                            raise

                if some_request_failed:
                    if not self._use_proxies:
                        # The cluster may have changed since last invocation
                        self._machines_cache = await self.machines()
                    if self._base_uri in self._machines_cache:
                        self._machines_cache.remove(self._base_uri)
            return response


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
            self._storage._etcd_client = ETCDClient(**etcd_options)
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

    async def _wait_for_lock(self, key, prev_exist=None, prev_index=None,
                             prev_value=None, update=False):
        '''
        *could* try setting the lock before we even get it and hope we get lucky.
        Would save us one trip to etcd
        '''
        # this method *should* use the wait_for with a timeout

        try:
            params = {}
            if prev_exist is not None:
                params['prevExist'] = prev_exist
            if prev_index is not None:
                params['prevIndex'] = prev_index
            if prev_value is not None:
                params['prevValue'] = prev_value
            await self._etcd_client.write(
                key, 'locked', ttl=self._lock_ttl, **params)
            return update
        except aio_etcd.EtcdAlreadyExist as ex:
            # next, try again with prevValue==unlocked
            return await self._wait_for_lock(key, prev_value='unlocked')
        except aio_etcd.EtcdCompareFailed as ex:
            logger.debug(f"start watch on {key} - {ex.payload['index']}")
            start = time.time()
            data = await self._etcd_client.watch(key, index=ex.payload['index'] + 1)
            logger.debug(f"finished watch on {key} - {ex.payload['index']} -- "
                         f"{time.time() - start} seconds")
            if data.value == 'unlocked':
                return await self._wait_for_lock(key, update=True,
                                                 prev_index=data.modifiedIndex)
            else:
                # try again
                return await self._wait_for_lock(key, update=True,
                                                 prev_value='unlocked')
        except (aio_etcd.EtcdKeyNotFound,) as ex:
            return await self._wait_for_lock(key, update=True)

    async def lock(self, obj):
        assert not obj.__new_marker__  # should be modifying an object
        if obj.__locked__:  # we've already locked this...
            return

        obj.__locked__ = True
        key = self._get_key(obj)

        try:
            if await asyncio.wait_for(self._wait_for_lock(key, prev_exist=False),
                                      timeout=self._etcd_acquire_timeout):
                # have lock; however, need to refresh object so we don't get
                # tid conflicts
                await self._transaction.refresh(obj)
        except asyncio.TimeoutError:
            self.status = Status.ABORTED
            await self._storage.abort(self._transaction)
            await self._transaction._cache.close(invalidate=False)
            self._transaction.tpc_cleanup()
            await self._transaction._manager._close_txn(self._transaction)
            raise ConflictError('Could not lock ob for writing')

        if obj._p_oid not in self._transaction.modified:
            # need to added it when locking...
            self._transaction.modified[obj._p_oid] = obj

    async def unlock(self, obj):
        if not obj.__locked__:
            # already unlocked
            return
        obj.__locked__ = False
        key = self._get_key(obj)
        await self._etcd_client.set(key, 'unlocked', ttl=self._lock_ttl)
