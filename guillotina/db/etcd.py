import aiohttp
import asyncio


class EtcdException(Exception):
    """
    Generic Etcd Exception.
    """
    pass


class EtcdError:
    # See https://github.com/coreos/etcd/blob/master/Documentation/errorcode.md
    """
    const (
    EcodeKeyNotFound    = 100
    EcodeTestFailed     = 101
    EcodeNotFile        = 102
    EcodeNoMorePeer     = 103
    EcodeNotDir         = 104
    EcodeNodeExist      = 105
    EcodeKeyIsPreserved = 106
    EcodeRootROnly      = 107

    EcodeValueRequired     = 200
    EcodePrevValueRequired = 201
    EcodeTTLNaN            = 202
    EcodeIndexNaN          = 203

    EcodeRaftInternal = 300
    EcodeLeaderElect  = 301

    EcodeWatcherCleared = 400
    EcodeEventIndexCleared = 401
    )

    // command related errors
    errors[100] = "Key Not Found"
    errors[101] = "Test Failed" //test and set
    errors[102] = "Not A File"
    errors[103] = "Reached the max number of peers in the cluster"
    errors[104] = "Not A Directory"
    errors[105] = "Already exists" // create
    errors[106] = "The prefix of given key is a keyword in etcd"
    errors[107] = "Root is read only"

    // Post form related errors
    errors[200] = "Value is Required in POST form"
    errors[201] = "PrevValue is Required in POST form"
    errors[202] = "The given TTL in POST form is not a number"
    errors[203] = "The given index in POST form is not a number"

    // raft related errors
    errors[300] = "Raft Internal Error"
    errors[301] = "During Leader Election"

    // etcd related errors
    errors[400] = "watcher is cleared due to etcd recovery"
    errors[401] = "The event in requested index is outdated and cleared"
    """

    error_exceptions = {
        100: KeyError,
        101: ValueError,
        102: KeyError,
        103: Exception,
        104: KeyError,
        105: KeyError,
        106: KeyError,
        200: ValueError,
        201: ValueError,
        202: ValueError,
        203: ValueError,
        300: Exception,
        301: Exception,
        400: Exception,
        401: EtcdException,
        500: EtcdException
    }

    @classmethod
    def handle(cls, errorCode=None, message=None, cause=None, **kwdargs):
        """ Decodes the error and throws the appropriate error message"""
        try:
            msg = "{} : {}".format(message, cause)
            exc = cls.error_exceptions[errorCode]
        except Exception:
            msg = "Unable to decode server response"
            exc = EtcdException
        raise exc(msg)


class Client:

    def __init__(
            self,
            host='127.0.0.1',
            port=2379,
            protocol='http',
            read_timeout=2,
            allow_redirect=True,
            allow_reconnect=False,
            loop=None,
    ):
        """
        Initialize the client.

        :param host: (optional) If a string, IP to connect to. If a tuple
            ((host, port),(host, port), ...) of known etcd nodes
        :type host: str or tuple
        :param int port: (optional) Port used to connect to etcd.
        :param int read_timeout: (optional) max seconds to wait for a read.
        :param bool allow_redirect: (optional) allow the client to connect to
            other nodes.
        :param str protocol:  (optional) Protocol used to connect to etcd.
        :param bool allow_reconnect: (optional) allow the client to reconnect
            to another etcd server in the cluster in the case the default one
            does not respond.
        :param loop: event loop to use internaly. If None, use
            asyncio.get_event_loop()
        """
        self.loop = loop if loop is not None else asyncio.get_event_loop()

        def uri(host, port):
            return '%s://%s:%d' % (protocol, host, port)

        if isinstance(host, tuple):
            self._machines_cache = [uri(*conn) for conn in host]
            self._base_uri = self._machines_cache[0]
        else:
            self._base_uri = uri(host, port)
            self._machines_cache = [self._base_uri]

        self.read_timeout = read_timeout
        self.allow_redirect = allow_redirect
        self.allow_reconnect = allow_reconnect
        self._conn = aiohttp.TCPConnector()
        self._cache_update_scheduled = True
        self.loop.create_task(self._update_machine_cache())

    # # high level operations

    async def get(self, key, **params):
        """
        Returns the value of the key 'key'. Use Client.read for more
        control and to get a full detailed EtcdResult

        :param str key:  Key.
        :returns: str value of the key
        :raises: KeyError if the key doesn't exists.
        """
        res = await self.read(key, **params)
        return res

    async def get_value(self, key):
        res = await self.read(key)
        if res.value is None:
            raise EtcdException(102)
        return res.value

    async def set(self, key, value, ttl=None, **params):
        """
        set the value of the key :param key: to the value :param value:. Is an
        alias of :method write: to expose a get/set API (with only most common
        args)

        """
        result = await self._write(key, value, ttl=ttl, **params)
        return result

    async def update(self, node, value, force_index=False):
        params = {}
        if force_index:
            return params

    async def delete(self, key, recursive=None, dir=None, **params):
        """
        Removed a key from etcd.
        :param str key:  Key.
        :param bool recursive: if we want to recursively delete a directory,
            set it to true
        :param bool dir: if we want to delete a directory, set it to true
        :param str prevValue: compare key to this value, and delete only if
            corresponding (optional).
        :param int prevIndex: modify key only if actual modifiedIndex matches
            the provided one (optional).

        :returns: EtcdResult

        :raises: KeyValue: if the key doesn't exists.
        """
        key = key.lstrip('/')

        if recursive is not None:
            params['recursive'] = recursive and "true" or "false"
        if dir is not None:
            dir['dir'] = dir and "true" or "false"

        response = await self._delete("/v2/keys/%s" % key, params=params)
        return await response.json()

    async def machines(self):
        resp = await self._get("/v2/machines")
        raw = await resp.text()
        return [m.strip() for m in raw.split(',')]

    async def read(self, key, loop=None, **params):
        """
        Returns the value of the key 'key'.

        :param str key:  Key.
        :param loop: the event loop to use for this request. Used internally
            for sync_read
        :param bool recursive (bool): If you should fetch recursively a dir
        :param bool wait (bool): If we should wait and return next time the
            key is changed
        :param int waitIndex (int): The index to fetch results from.
        :param bool sorted (bool): Sort the output keys (alphanumerically)
        :param int timeout (int):  max seconds to wait for a read.

        :returns:
            EtcdResult (or an array of client.EtcdResult if a
            subtree is queried)

        :raises:
            KeyValue:  If the key doesn't exists.
            asyncio.TimeoutError
        """
        loop = loop if loop is not None else self.loop
        timeout = params.get('timeout', self.read_timeout)
        key = key.lstrip('/')
        for (k, v) in params.items():
            if type(v) == bool:
                params[k] = v and "true" or "false"
            else:
                params[k] = v
        response = await self._get(
            "/v2/keys/%s" % key, params=params, timeout=timeout, loop=loop
        )
        return await response.json()

    async def _write(self, key, value, append=False, **params):
        """
        Writes the value for a key, possibly doing atomit Compare-and-Swap

        Args:
        :param str key:  Key.
        :param str value:  value to set
        :param int ttl:  Time in seconds of expiration (optional).
        :param bool dir: Set to true if we are writing a directory; default is
            false.
        :param bool append: If true, it will post to append the new value to
            the dir, creating a sequential key. Defaults to false.
        :param str prevValue: compare key to this value, and swap only if
            corresponding (optional).
        :param int prevIndex: modify key only if actual modifiedIndex matches
            the provided one (optional).
        :param bool prevExist: If false, only create key; if true, only update
            key.

        Returns:
            client.EtcdResult
        """
        key = key.lstrip('/')
        # params = {}
        if value is not None:
            params['value'] = value
        if params.get('dir', False):
            if value:
                raise EtcdException(
                    'Cannot create a directory with a value')
        for (k, v) in list(params.items()):
            if type(v) == bool:
                params[k] = v and "true" or "false"
            elif v is None:
                del params[k]

        method = append and self._post or self._put
        path = "/v2/keys/%s" % key
        response = await method(path, params=params)
        return await response.json()

    async def _get(self, path, params=None, timeout=None, loop=None):
        resp = await self._execute('get', path, params, timeout, loop)
        return resp

    async def _put(self, path, params=None, timeout=None):
        resp = await self._execute('put', path, params, timeout)
        return resp

    async def _post(self, path, params=None, timeout=None):
        resp = await self._execute('post', path, params, timeout)
        return resp

    async def _delete(self, path, params=None, timeout=None):
        resp = await self._execute('delete', path, params, timeout)
        return resp

    async def _update_machine_cache(self):
        if self.allow_reconnect:
            self._machine_cache = await self.machines()
        self._cache_update_scheduled = False

    async def _execute(self, method, path, params=None, timeout=None, loop=None):
        if loop is None:
            loop = self.loop
        if timeout is None:
            timeout = self.read_timeout
        failed = False
        # TODO: whatif self._machines_cache is empty ?
        for idx, uri in enumerate(self._machines_cache):
            try:
                resp = await asyncio.wait_for(
                    aiohttp.request(
                        method, uri + path, params=params, loop=loop
                    ),
                    timeout, loop=loop
                )
                if failed:
                    self._machine_cache = self._machine_cache[idx:]
                    if not self._cache_update_scheduled:
                        self._cache_update_scheduled = True
                        self.loop.create_task(self._update_machine_cache())
                return resp
            except asyncio.TimeoutError:
                failed = True
        raise asyncio.TimeoutError()
