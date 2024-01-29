from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.content import DefaultOPTIONS
from guillotina.api.service import DownloadService
from guillotina.api.service import TraversableFieldService
from guillotina.component import get_multi_adapter
from guillotina.event import notify
from guillotina.events import ObjectModifiedEvent
from guillotina.exceptions import FileNotFoundException
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IResource
from guillotina.interfaces import IStaticDirectory
from guillotina.interfaces import IStaticFile
from guillotina.response import HTTPNotFound
from guillotina.response import Response

import mimetypes


def _traversed_file_doc(summary, parameters=None, responses=None):
    parameters = parameters or []
    responses = responses or {"200": {"description": "Successfully updated content"}}
    return {
        "traversed_service_definitions": {
            "{field_name}": {
                "summary": summary,
                "parameters": [
                    {
                        "name": "field_name",
                        "in": "path",
                        "description": "Name of file field",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ]
                + parameters,
                "responses": responses,
            }
        }
    }


TUS_PARAMETERS = [
    {"name": "Upload-Offset", "in": "headers", "required": True, "schema": {"type": "integer"}},
    {"name": "UPLOAD-LENGTH", "in": "headers", "required": True, "schema": {"type": "integer"}},
    {"name": "UPLOAD-MD5", "in": "headers", "required": False, "schema": {"type": "string"}},
    {"name": "UPLOAD-EXTENSION", "in": "headers", "required": False, "schema": {"type": "string"}},
    {"name": "TUS-RESUMABLE", "in": "headers", "required": True, "schema": {"type": "string"}},
    {"name": "UPLOAD-METADATA", "in": "headers", "required": False, "schema": {"type": "string"}},
]

# Static File
@configure.service(context=IStaticFile, method="GET", permission="guillotina.AccessContent")
class FileGET(DownloadService):
    async def serve_file(self, fi):
        filepath = str(fi.file_path.absolute())
        filename = fi.file_path.name
        with open(filepath, "rb") as f:
            resp = Response(status=200)
            resp.content_type, _ = mimetypes.guess_type(filename)

            disposition = 'filename="{}"'.format(filename)
            if "text" not in (resp.content_type or ""):
                disposition = "attachment; " + disposition

            resp.headers["CONTENT-DISPOSITION"] = disposition

            data = f.read()
            resp.content_length = len(data)
            await resp.prepare(self.request)
            await resp.write(data, eof=True)
            return resp

    async def __call__(self):
        if hasattr(self.context, "file_path"):
            return await self.serve_file(self.context)


@configure.service(context=IStaticDirectory, method="GET", permission="guillotina.AccessContent")
class DirectoryGET(FileGET):
    async def __call__(self):
        for possible_default_file in app_settings["default_static_filenames"]:
            if possible_default_file in self.context:
                return await self.serve_file(self.context[possible_default_file])


# Field File
@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ModifyContent",
    name="@upload/{field_name}",
    **_traversed_file_doc("Update the content of a file"),
)
@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ModifyContent",
    name="@upload/{field_name}/{file_key}",
    **_traversed_file_doc(
        "Update the content of a file",
        parameters=[{"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}}],
    ),
)
class UploadFile(TraversableFieldService):
    async def __call__(self):
        if self.behavior is not None and IAsyncBehavior.implementedBy(self.behavior.__class__):
            # providedBy not working here?
            await self.behavior.load(create=True)
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
        return await adapter.upload()


@configure.service(
    context=IResource,
    method="DELETE",
    permission="guillotina.DeleteContent",
    name="@delete/{field_name}",
    **_traversed_file_doc("Update the content of a file"),
)
@configure.service(
    context=IResource,
    method="DELETE",
    permission="guillotina.DeleteContent",
    name="@delete/{field_name}/{file_key}",
    **_traversed_file_doc(
        "Update the content of a file",
        parameters=[{"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}}],
    ),
)
class DeleteFile(TraversableFieldService):
    async def __call__(self):
        if self.behavior is not None and IAsyncBehavior.implementedBy(self.behavior.__class__):
            # providedBy not working here?
            await self.behavior.load(create=True)
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
        result = await adapter.delete()
        self.context.register()
        await notify(ObjectModifiedEvent(self.context))
        return result


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    name="@download/{field_name}",
    **_traversed_file_doc(
        "Download the content of a file",
        parameters=[{"name": "filename", "in": "query", "required": False, "schema": {"type": "string"}}],
    ),
)
@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.ViewContent",
    name="@download/{field_name}/{file_key}",
    **_traversed_file_doc(
        "Download the content of a file",
        parameters=[
            {"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}},
            {"name": "filename", "in": "query", "required": False, "schema": {"type": "string"}},
        ],
    ),
)
class DownloadFile(TraversableFieldService):
    async def handle(self, adapter, kwargs):
        return await adapter.download(**kwargs)

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        kwargs = {}
        filename = self.request.query.get("filename")
        if filename is not None:
            kwargs["filename"] = filename
        try:
            adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
            return await self.handle(adapter, kwargs)
        except (AttributeError, FileNotFoundException):
            # file does not exist
            return HTTPNotFound(content={"reason": "File does not exist"})


@configure.service(
    context=IResource,
    method="HEAD",
    permission="guillotina.ViewContent",
    name="@download/{field_name}",
    **_traversed_file_doc("HEAD download"),
)
@configure.service(
    context=IResource,
    method="HEAD",
    permission="guillotina.ViewContent",
    name="@download/{field_name}/{file_key}",
    **_traversed_file_doc(
        "HEAD download",
        parameters=[{"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}}],
    ),
)
class HeadFile(DownloadFile):
    async def handle(self, adapter, kwargs):
        return await adapter.head(**kwargs)


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ModifyContent",
    name="@tusupload/{field_name}",
    **_traversed_file_doc(
        "TUS endpoint",
        parameters=TUS_PARAMETERS,
        responses={
            "204": {
                "description": "Successfully patched data",
                "headers": {
                    "Location": {"schema": {"type": "string"}},
                    "Tus-Resumable": {"schema": {"type": "string"}},
                    "Access-Control-Expose-Headers": {"schema": {"type": "string"}},
                },
            }
        },
    ),
)
@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ModifyContent",
    name="@tusupload/{field_name}/{file_key}",
    **_traversed_file_doc(
        "TUS endpoint",
        parameters=[{"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}}]
        + TUS_PARAMETERS,
        responses={
            "204": {
                "description": "Successfully patched data",
                "headers": {
                    "Location": {"schema": {"type": "string"}},
                    "Tus-Resumable": {"schema": {"type": "string"}},
                    "Access-Control-Expose-Headers": {"schema": {"type": "string"}},
                },
            }
        },
    ),
)
class TusCreateFile(UploadFile):
    async def __call__(self):
        if self.behavior is not None and IAsyncBehavior.implementedBy(self.behavior.__class__):
            # providedBy not working here?
            await self.behavior.load(create=True)
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
        return await adapter.tus_create()


@configure.service(
    context=IResource,
    method="HEAD",
    permission="guillotina.ModifyContent",
    name="@tusupload/{field_name}/{file_key}",
    **_traversed_file_doc(
        "TUS endpoint",
        parameters=[{"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}}],
        responses={
            "204": {
                "description": "Successfully patched data",
                "headers": {
                    "Location": {"schema": {"type": "string"}},
                    "Tus-Resumable": {"schema": {"type": "string"}},
                    "Access-Control-Expose-Headers": {"schema": {"type": "string"}},
                },
            }
        },
    ),
)
@configure.service(
    context=IResource,
    method="HEAD",
    permission="guillotina.ModifyContent",
    name="@tusupload/{field_name}",
    **_traversed_file_doc(
        "TUS endpoint",
        responses={
            "200": {
                "description": "Successfully patched data",
                "headers": {
                    "Location": {"schema": {"type": "string"}},
                    "Tus-Resumable": {"schema": {"type": "string"}},
                    "Access-Control-Expose-Headers": {"schema": {"type": "string"}},
                },
            }
        },
    ),
)
class TusHeadFile(UploadFile):
    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
        return await adapter.tus_head()


@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ModifyContent",
    name="@tusupload/{field_name}",
    **_traversed_file_doc(
        "TUS endpoint",
        parameters=[
            {"name": "Upload-Offset", "in": "headers", "required": True, "schema": {"type": "integer"}},
            {"name": "CONTENT-LENGTH", "in": "headers", "required": True, "schema": {"type": "integer"}},
        ],
        responses={
            "204": {
                "description": "Successfully patched data",
                "headers": {"Upload-Offset": {"schema": {"type": "integer"}}},
            }
        },
    ),
)
@configure.service(
    context=IResource,
    method="PATCH",
    permission="guillotina.ModifyContent",
    name="@tusupload/{field_name}/{file_key}",
    **_traversed_file_doc(
        "TUS endpoint",
        parameters=[
            {"name": "Upload-Offset", "in": "headers", "required": True, "schema": {"type": "integer"}},
            {"name": "CONTENT-LENGTH", "in": "headers", "required": True, "schema": {"type": "integer"}},
            {"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}},
        ],
        responses={
            "204": {
                "description": "Successfully patched data",
                "headers": {"Upload-Offset": {"schema": {"type": "integer"}}},
            }
        },
    ),
)
class TusPatchFile(UploadFile):
    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
        return await adapter.tus_patch()


@configure.service(
    context=IResource,
    method="OPTIONS",
    permission="guillotina.AccessPreflight",
    name="@tusupload/{field_name}",
    **_traversed_file_doc(
        "TUS endpoint",
        responses={
            "200": {
                "description": "Successfully returned tus info",
                "headers": {
                    "Tus-Version": {"schema": {"type": "string"}},
                    "Tus-Resumable": {"schema": {"type": "string"}},
                    "Tus-Max-Size": {"schema": {"type": "string"}},
                    "Tus-Extension": {"schema": {"type": "string"}},
                },
            }
        },
    ),
)
@configure.service(
    context=IResource,
    method="OPTIONS",
    permission="guillotina.AccessPreflight",
    name="@tusupload/{field_name}/{file_key}",
    **_traversed_file_doc(
        "TUS endpoint",
        parameters=[{"name": "file_key", "in": "path", "required": True, "schema": {"type": "string"}}],
        responses={
            "200": {
                "description": "Successfully returned tus info",
                "headers": {
                    "Tus-Version": {"schema": {"type": "string"}},
                    "Tus-Resumable": {"schema": {"type": "string"}},
                    "Tus-Max-Size": {"schema": {"type": "string"}},
                    "Tus-Extension": {"schema": {"type": "string"}},
                },
            }
        },
    ),
)
class TusOptionsFile(DefaultOPTIONS, UploadFile):
    async def render(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = get_multi_adapter((self.context, self.request, self.field), IFileManager)
        return await adapter.tus_options()
