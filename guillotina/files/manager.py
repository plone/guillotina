from guillotina import configure
from guillotina._settings import app_settings
from guillotina.component import get_multi_adapter
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.utils import import_class
from zope.interface import alsoProvides


@configure.adapter(
    for_=(IResource, IRequest, ICloudFileField),
    provides=IFileManager)
class CloudFileManager(object):

    def __init__(self, context, request, field):
        iface = import_class(app_settings['cloud_storage'])
        alsoProvides(field, iface)
        self.real_file_manager = get_multi_adapter(
            (context, request, field), IFileManager)

    async def download(self, *args, **kwargs):
        return await self.real_file_manager.download(*args, **kwargs)

    async def tus_options(self, *args, **kwargs):
        return await self.real_file_manager.tus_options(*args, **kwargs)

    async def tus_head(self, *args, **kwargs):
        return await self.real_file_manager.tus_head(*args, **kwargs)

    async def tus_patch(self, *args, **kwargs):
        return await self.real_file_manager.tus_patch(*args, **kwargs)

    async def tus_create(self, *args, **kwargs):
        return await self.real_file_manager.tus_create(*args, **kwargs)

    async def upload(self, *args, **kwargs):
        return await self.real_file_manager.upload(*args, **kwargs)

    async def iter_data(self, *args, **kwargs):
        async for chunk in self.real_file_manager.iter_data(*args, **kwargs):
            yield chunk

    async def save_file(self, generator, *args, **kwargs):
        return await self.real_file_manager.save_file(generator, *args, **kwargs)
