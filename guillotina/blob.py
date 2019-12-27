from guillotina._settings import app_settings
from guillotina.exceptions import BlobChunkNotFound
from guillotina.transactions import get_transaction
from io import BytesIO
from typing import AsyncIterator
from typing import Union


class Blob:
    """
    Blob object is meant to be used with a resource object.

    Example usages would be:

        ob.blob = Blob(ob)
        blobfi = ob.blob.open()
        data = await blob.async_read()
    """

    chunk_sizes = None

    def __init__(self, resource):
        self.bid = app_settings["uid_generator"](resource)
        self.resource_uid = resource.__uuid__
        self.size = 0
        self.chunks = 0
        self.chunk_sizes = {}

    def open(self, mode="r", transaction=None):
        return BlobFile(self, mode, transaction)


class BlobFile:

    _started_writing = False

    def __init__(self, blob, mode, transaction=None):
        self.blob = blob
        self.mode = mode
        if transaction is None:
            transaction = get_transaction()
        if transaction is None:
            raise Exception("Can not find transaction to work on blob with")
        self.transaction = transaction

    async def async_del(self):
        await self.transaction.del_blob(self.blob.bid)
        self.blob.chunk_sizes = {}
        self.blob.size = 0
        self.blob.chunks = 0

    async def async_write_chunk(self, data: bytes):
        if self.mode not in ("w", "a"):
            raise Exception("You are not allowed to write blob data with mode {}".format(self.mode))

        if self.mode == "w" and not self._started_writing:
            # we're writing a new set of blobs, delete existing blobs...
            await self.transaction.del_blob(self.blob.bid)
            self.blob.size = 0
            self.blob.chunks = 0
            self.blob.chunk_sizes = {}

        self._started_writing = True

        await self.transaction.write_blob_chunk(self.blob.bid, self.blob.resource_uid, self.blob.chunks, data)

        if self.blob.chunk_sizes is not None:
            self.blob.chunk_sizes[self.blob.chunks] = len(data)

        self.blob.chunks += 1
        self.blob.size += len(data)

    async def async_write(self, data: Union[bytes, BytesIO], chunk_size: int = 1024 * 1024 * 1):
        if isinstance(data, bytes):
            stream = BytesIO(data)
        else:
            stream = data

        data = stream.read(chunk_size)
        while data:
            await self.async_write_chunk(data)
            data = stream.read(chunk_size)

    async def async_read_chunk(self, chunk_index) -> bytes:
        try:
            return (await self.transaction.read_blob_chunk(self.blob.bid, chunk_index))["data"]
        except (KeyError, TypeError, IndexError):
            raise BlobChunkNotFound("Could not find blob({}), chunk({})".format(self.blob.bid, chunk_index))

    async def iter_async_read(self) -> AsyncIterator[bytes]:
        """
        yield chunks of data...
        """
        for chunk_index in range(self.blob.chunks):
            yield await self.async_read_chunk(chunk_index)

    async def async_read(self, chunk_size=None) -> bytes:
        """
        read all the data... should this implement complete file-like api?
        """
        data = b""
        async for chunk in self.iter_async_read():
            data += chunk
        return data
