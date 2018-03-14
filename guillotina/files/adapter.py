from .dbfile import DBFile
from guillotina import configure
from guillotina.blob import Blob
from guillotina.interfaces import IDBFileField
from guillotina.interfaces import IFileCleanup
from guillotina.interfaces import IFileStorageManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IUploadDataManager


@configure.adapter(
    for_=IFileStorageManager,
    provides=IUploadDataManager)
class DBDataManager:

    _file = None

    def __init__(self, file_storage_manager):
        self.file_storage_manager = file_storage_manager
        self.context = file_storage_manager.context
        self.request = file_storage_manager.request
        self.field = file_storage_manager.field
        self._file = None

    @property
    def real_context(self):
        return self.field.context or self.context

    async def load(self):
        file = self.field.get(self.real_context)
        if not isinstance(file, self.file_storage_manager.file_class):
            file = self.file_storage_manager.file_class()
            self.field.set(self.real_context, file)
            await self.save()
        self._file = file

    async def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self._file, key, value)
        await self.save()

    async def save(self):
        try:
            self.field.context.data._p_register()
        except AttributeError:
            self.field.context._p_register()

    async def finish(self):
        pass

    @property
    def content_type(self):
        if not self._file.content_type:
            return self._file.guess_content_type()
        return self._file.content_type

    @property
    def size(self):
        if self._file.size:
            return self._file.size
        return 0

    @property
    def file(self):
        return self._file

    def get_offset(self):
        return self._file.get_actual_size()

    def get(self, name, default=None):
        return getattr(self._file, name, default)


@configure.adapter(
    for_=IResource,
    provides=IFileCleanup
)
class DefaultFileCleanup:
    def __init__(self, context):
        pass

    def should_clean(self, **kwargs):
        return True


@configure.adapter(
    for_=(IResource, IRequest, IDBFileField),
    provides=IFileStorageManager)
class DBFileStorageManagerAdapter:

    file_class = DBFile

    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

    async def start(self, dm):
        await dm.update(current_upload=0)
        if dm._file._blob is not None:
            bfile = dm._file._blob.open('r')
            await bfile.async_del()
        blob = Blob(dm.context)
        dm._file._blob = blob
        await dm.save()

    async def iter_data(self, dm):
        bfile = dm._file._blob.open()
        async for chunk in bfile.iter_async_read():
            yield chunk

    async def append(self, dm, data):
        mode = 'a'
        if dm._file._blob.chunks == 0:
            mode = 'w'
        bfile = dm._file._blob.open(mode)
        await bfile.async_write_chunk(data)
        await dm.update(current_upload=dm._file.size)

    async def finish(self, dm):
        await dm.save()

    async def copy(self, dm, from_storage_manager, from_dm):
        async for chunk in from_storage_manager.iter_data(from_dm):
            await from_storage_manager.append(from_dm, chunk)
        await from_storage_manager.finish(from_dm)
