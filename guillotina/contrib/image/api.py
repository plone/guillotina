from functools import partial
from guillotina import configure
from guillotina.api.files import _traversed_file_doc
from guillotina.api.files import DownloadFile
from guillotina.api.service import TraversableFieldService
from guillotina.component import get_multi_adapter
from guillotina.contrib.image.interfaces import IImagingSettings
from guillotina.contrib.image.preview import CloudPreviewImageFileField
from guillotina.contrib.image.scale import scaleImage
from guillotina.interfaces import IFileManager
from guillotina.interfaces.content import IResource
from guillotina.response import HTTPNoContent
from guillotina.response import HTTPNotFound
from guillotina.schema.interfaces import IOrderedDict
from guillotina.utils import get_registry
from guillotina.utils import run_async
from io import BytesIO


BUFFER = 262144


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    name="@images/{field_name}",
    **_traversed_file_doc("Download the image"),
)
class DownloadImageFile(DownloadFile):
    pass


@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ViewContent",
    name="@images/{field_name}/{scale}",
    **_traversed_file_doc("Download the image scale"),
)
@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ViewContent",
    name="@images/{field_name}/{file_key}/{scale}",
    **_traversed_file_doc("Download the image scale"),
)
class UpdateImageScale(TraversableFieldService):
    async def __call__(self):
        registry = await get_registry()
        settings = registry.for_interface(IImagingSettings)
        field_name = self.request.matchdict["field_name"]
        if "file_key" in self.request.matchdict:
            field_name = f"{field_name}_{self.request.matchdict['file_key']}"
        scale_name = self.request.matchdict["scale"]
        allowed_sizes = settings["allowed_sizes"]
        if scale_name not in allowed_sizes:
            raise HTTPNotFound(content={"reason": f"{scale_name} is not supported"})

        file = self.field.get(self.field.context or self.context)
        if file is None:
            raise HTTPNotFound(content={"message": "File or custom filename required to download"})

        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)

        data = b""
        async for chunk in adapter.iter_data():
            data += chunk

        width, _, height = allowed_sizes[scale_name].partition(":")

        result, format_, size = await run_async(
            scaleImage,
            data,
            int(width),
            int(height),
            quality=settings["quality"],
            direction="thumbnail",
        )

        async def generator(data):
            buf = BytesIO(data)
            buf.seek(0)
            contents = buf.read(BUFFER)
            while len(contents):
                yield contents
                contents = buf.read(BUFFER)

        if not hasattr(file, "previews"):
            file.previews = {}

        new_field = CloudPreviewImageFileField(__name__=scale_name, file=file).bind(
            self.behavior or self.context
        )
        adapter = get_multi_adapter((self.context, self.request, new_field), IFileManager)

        await adapter.save_file(
            partial(generator, result),
            content_type=f"image/{format_}",
            filename=f"{field_name}_{scale_name}.{format_}",
            extension=format_,
            size=len(result),
        )
        self.context.register()


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    name="@images/{field_name}/{scale}",
    **_traversed_file_doc("Download the image scale"),
)
@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    name="@images/{field_name}/{file_key}/{scale}",
    **_traversed_file_doc("Download the image scale"),
)
class DownloadImageScale(TraversableFieldService):
    async def __call__(self):
        registry = await get_registry()
        settings = registry.for_interface(IImagingSettings)
        scale_name = self.request.matchdict["scale"]
        allowed_sizes = settings["allowed_sizes"]
        if scale_name not in allowed_sizes:
            raise HTTPNotFound(content={"reason": f"{scale_name} is not supported"})

        file = self.field.get(self.field.context or self.context)
        if file is None:
            raise HTTPNotFound(content={"message": "File or custom filename required to download"})

        if hasattr(file, "previews") and file.previews is not None and scale_name in file.previews:
            new_field = CloudPreviewImageFileField(__name__=scale_name, file=file).bind(
                self.behavior or self.context
            )
            adapter = get_multi_adapter((self.context, self.request, new_field), IFileManager)
            return await adapter.download()
        else:
            return HTTPNoContent()


@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ViewContent",
    name="@sort/{field_name}",
    **_traversed_file_doc("Order the keys of a field"),
)
class OrderMultiImage(TraversableFieldService):
    async def __call__(self):
        if IOrderedDict.providedBy(self.field):
            data = await self.request.json()
            self.field.reorder_images(data)
