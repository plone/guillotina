from .field import BaseCloudFile
from guillotina.blob import Blob
from guillotina.event import notify
from guillotina.events import FileUploadFinishedEvent
from guillotina.interfaces import IDBFile
from guillotina.interfaces import IFileCleanup
from zope.interface import implementer

import uuid


@implementer(IDBFile)
class DBFile(BaseCloudFile):
    """File stored in a DB using blob storage"""

    _blob = None

    @property
    def valid(self):
        return self._blob is not None

    async def init_upload(self, context):
        context._p_register()

        self._old_uri = self.uri
        self._old_size = self.size
        self._old_filename = self.filename
        self._old_md5 = self.md5
        self._old_content_type = self.guess_content_type()

        self._current_upload = 0
        if self._blob is not None:
            cleanup = IFileCleanup(context, None)
            if cleanup is None or cleanup.should_clean(file=self):
                bfile = self._blob.open('r')
                await bfile.async_del()
            else:
                self._previous_blob = self._blob
        blob = Blob(context)
        self._uri = uuid.uuid4().hex
        self._blob = blob

    async def append_data(self, context, data):
        context._p_register()
        mode = 'a'
        if self._blob.chunks == 0:
            mode = 'w'
        bfile = self._blob.open(mode)
        await bfile.async_write_chunk(data)
        self._current_upload = self._blob.size

    def get_actual_size(self):
        return self._blob.size

    async def finish_upload(self, context):
        await notify(FileUploadFinishedEvent(context))

    async def download(self, context, resp):
        bfile = self._blob.open()
        async for chunk in bfile.iter_async_read():
            resp.write(chunk)
            await resp.drain()
        return resp

    async def iter_data(self, context):
        bfile = self._blob.open()
        async for chunk in bfile.iter_async_read():
            yield chunk

    async def copy_cloud_file(self, context, new_uri=None):
        if self._blob is None:
            return
        existing_blob = self._blob
        self._blob = None  # make sure to set None or init will delete it!
        await self.init_upload(context)

        existing_bfile = existing_blob.open('r', context._p_jar)
        bfile = self._blob.open('w', context._p_jar)
        async for chunk in existing_bfile.iter_async_read():
            await bfile.async_write_chunk(chunk)
        self._current_upload = self._blob.size
