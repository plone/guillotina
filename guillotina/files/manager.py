from .const import CHUNK_SIZE
from .exceptions import RangeException
from aiohttp.web import StreamResponse
from guillotina import configure
from guillotina import glogging
from guillotina._settings import app_settings
from guillotina.component import get_adapter
from guillotina.component import get_multi_adapter
from guillotina.files.utils import read_request_data
from guillotina.interfaces import ICloudFileField
from guillotina.interfaces import IFileManager
from guillotina.interfaces import IFileStorageManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IUploadDataManager
from guillotina.response import HTTPClientClosedRequest
from guillotina.response import HTTPConflict
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPRequestRangeNotSatisfiable
from guillotina.response import Response
from guillotina.utils import apply_coroutine
from guillotina.utils import get_object_url
from guillotina.utils import resolve_dotted_name
from zope.interface import alsoProvides

import asyncio
import base64
import posixpath
import uuid


logger = glogging.getLogger("guillotina")


@configure.adapter(for_=(IResource, IRequest, ICloudFileField), provides=IFileManager)
class FileManager(object):
    def __init__(self, context, request, field):
        self.context = context
        self.request = request
        self.field = field

        iface = resolve_dotted_name(app_settings["cloud_storage"])
        alsoProvides(field, iface)

        self.file_storage_manager = get_multi_adapter((context, request, field), IFileStorageManager)
        self.dm = get_adapter(
            self.file_storage_manager, IUploadDataManager, name=app_settings.get("cloud_datamanager") or "db"
        )

    async def prepare_download(
        self,
        disposition=None,
        filename=None,
        content_type=None,
        size=None,
        extra_headers=None,
        status=200,
        **kwargs,
    ):
        if disposition is None:
            disposition = self.request.query.get("disposition", "attachment")

        try:
            file = self.field.get(self.field.context or self.context)
        except AttributeError:  # pragma: no cover
            file = None

        if file is None and filename is None:  # pragma: no cover
            raise HTTPNotFound(content={"message": "File or custom filename required to download"})
        cors_renderer = app_settings["cors_renderer"](self.request)
        headers = await cors_renderer.get_headers()
        headers.update(extra_headers or {})
        headers.update(
            {"Content-Disposition": '{}; filename="{}"'.format(disposition, filename or file.filename)}
        )

        if kwargs.get("range_supported", True) and await self._range_supported():
            headers["Accept-Ranges"] = "bytes"
        else:  # pragma: no cover
            headers["Accept-Ranges"] = "none"

        download_resp = StreamResponse(headers=headers, status=status)
        download_resp.content_type = content_type or file.guess_content_type()
        if size or file.size:
            download_resp.content_length = size or file.size

        await download_resp.prepare(self.request)
        return download_resp

    async def head(
        self, disposition=None, filename=None, content_type=None, size=None, extra_headers=None, **kwargs
    ):
        try:
            if hasattr(self.file_storage_manager, "exists"):
                # does not need to implement but can be a way to verify
                # file exists on cloud platform still
                if not await apply_coroutine(self.file_storage_manager.exists):
                    raise HTTPNotFound(content={"message": "File object does not exist"})
            download_resp = await self.prepare_download(
                disposition, filename, content_type, size, extra_headers, **kwargs
            )
            await download_resp.write_eof()
        except (ConnectionRefusedError, ConnectionResetError):  # pragma: no cover
            logger.info(f"Head cancelled: {self.request}")
            # when supporting range headers, the browser will
            # cancel downloads. This is fine.
            raise HTTPClientClosedRequest()
        return download_resp

    async def _range_supported(self) -> bool:
        try:
            return await self.file_storage_manager.range_supported()
        except AttributeError:  # pragma: no cover
            return False

    async def download(self, **kwargs):
        if (
            kwargs.get("range_supported", True)
            and "Range" in self.request.headers
            and await self._range_supported()
        ):
            return await self._range_download(**kwargs)
        else:
            return await self._full_download(**kwargs)

    async def _range_download(
        self,
        disposition=None,
        filename=None,
        content_type=None,
        size=None,
        extra_headers=None,
        range_supported=True,
        **kwargs,
    ):
        try:
            file = self.field.get(self.field.context or self.context)
        except AttributeError:  # pragma: no cover
            raise HTTPNotFound()

        range_request = self.request.headers["Range"]
        try:
            start, _, end = range_request.split("bytes=")[-1].partition("-")
            start = int(start)
            if len(end) == 0:
                # bytes=0- is valid
                end = file.size - 1
            end = int(end) + 1  # python is inclusive, http is exclusive
        except (IndexError, ValueError):
            # range errors fallback to full download
            raise HTTPRequestRangeNotSatisfiable(
                content={"reason": "rangeNotParsable", "range": range_request},
                headers={"Content-Range": f"bytes */{file.size}"},
            )
        if start > end or start < 0:
            raise HTTPRequestRangeNotSatisfiable(
                content={"reason": "invalidRange", "range": range_request, "message": "Invalid range"},
                headers={"Content-Range": f"bytes */{file.size}"},
            )
        if end > file.size:
            raise HTTPRequestRangeNotSatisfiable(
                content={
                    "reason": "invalidRange",
                    "range": range_request,
                    "message": "Invalid range, too large end value",
                },
                headers={"Content-Range": f"bytes */{file.size}"},
            )

        logger.debug(f"Range request: {range_request} {self.request}")
        if extra_headers is None:
            extra_headers = {}
        extra_headers["Content-Range"] = f"bytes {start}-{end - 1}/{file.size}"

        try:
            download_resp = await self.prepare_download(
                disposition,
                filename,
                content_type,
                end - start,
                extra_headers,
                status=206,
                range_supported=range_supported,
                **kwargs,
            )

            found = 0
            try:
                async for chunk in self.file_storage_manager.read_range(start, end):
                    found += len(chunk)
                    logger.info(f"Got chunk {range_request}: {len(chunk)}/{end - start}|{found}")
                    await download_resp.write(chunk)
                    await download_resp.drain()
            except RangeException:
                raise HTTPRequestRangeNotSatisfiable(
                    content={
                        "reason": "rangeNotFound",
                        "range": range_request,
                        "message": "Could not read range correctly",
                    },
                    headers={"Content-Range": f"bytes */{file.size}"},
                )
        except (asyncio.CancelledError, ConnectionRefusedError, ConnectionResetError):  # pragma: no cover
            logger.info(f"Range cancelled: {range_request} {self.request}")
            # when supporting range headers, the browser will
            # cancel downloads. This is fine.
            raise HTTPClientClosedRequest()
        finally:
            await download_resp.write_eof()
            return download_resp

    async def _full_download(
        self,
        disposition=None,
        filename=None,
        content_type=None,
        size=None,
        extra_headers=None,
        range_supported=True,
        **kwargs,
    ):
        download_resp = None
        try:
            async for chunk in self.file_storage_manager.iter_data(**kwargs):
                if download_resp is None:
                    # defer to make sure we do http exception handling
                    # before data starts streaming properly
                    download_resp = await self.prepare_download(
                        disposition,
                        filename,
                        content_type,
                        size,
                        extra_headers,
                        range_supported=range_supported,
                        **kwargs,
                    )
                await download_resp.write(chunk)
                await download_resp.drain()
        except (asyncio.CancelledError, ConnectionRefusedError, ConnectionResetError):  # pragma: no cover
            logger.info(f"Download cancelled: {self.request}")
            # when supporting range headers, the browser will
            # cancel downloads. This is fine.
            if download_resp is None:
                raise HTTPClientClosedRequest()
        else:
            if download_resp is None:
                # deferred
                download_resp = await self.prepare_download(
                    disposition,
                    filename,
                    content_type,
                    size,
                    extra_headers,
                    range_supported=range_supported,
                    **kwargs,
                )
            await download_resp.write_eof()
            return download_resp

    async def tus_options(self, *args, **kwargs):
        resp = Response(
            headers={
                "Tus-Resumable": "1.0.0",
                "Tus-Version": "1.0.0",
                "Tus-Extension": "creation-defer-length",
            }
        )
        return resp

    async def tus_head(self, *args, **kwargs):
        await self.dm.load()
        head_response = {
            "Upload-Offset": str(self.dm.get_offset()),
            "Tus-Resumable": "1.0.0",
            "Access-Control-Expose-Headers": "Upload-Offset,Tus-Resumable,Upload-Length",
        }
        if self.dm.get("size"):
            head_response["Upload-Length"] = str(self.dm.get("size"))
        else:
            head_response["Upload-Length"] = "0"
        return Response(headers=head_response)

    async def _iterate_request_data(self):
        self.request._last_read_pos = 0
        data = await read_request_data(self.request, CHUNK_SIZE)

        while data:
            yield data
            data = await read_request_data(self.request, CHUNK_SIZE)

    async def tus_patch(self, *args, **kwargs):
        await self.dm.load()
        to_upload = None
        if "CONTENT-LENGTH" in self.request.headers:
            # header is optional, we'll be okay with unknown lengths...
            to_upload = int(self.request.headers["CONTENT-LENGTH"])

        if "UPLOAD-LENGTH" in self.request.headers:
            if self.dm.get("deferred_length"):
                size = int(self.request.headers["UPLOAD-LENGTH"])
                await self.dm.update(size=size)

        if "UPLOAD-OFFSET" in self.request.headers:
            offset = int(self.request.headers["UPLOAD-OFFSET"])
        else:
            raise HTTPPreconditionFailed(content={"reason": "No upload-offset header"})

        ob_offset = self.dm.get("offset")
        if offset != ob_offset:
            raise HTTPConflict(
                content={
                    "reason": f"Current upload offset({offset}) does not match " f"object offset {ob_offset}"
                }
            )

        read_bytes = await self.file_storage_manager.append(self.dm, self._iterate_request_data(), offset)

        if to_upload and read_bytes != to_upload:  # pragma: no cover
            # check length matches if provided
            raise HTTPPreconditionFailed(content={"reason": "Upload size does not match what was provided"})
        await self.dm.update(offset=offset + read_bytes)

        headers = {
            "Upload-Offset": str(self.dm.get_offset()),
            "Tus-Resumable": "1.0.0",
            "Access-Control-Expose-Headers": ",".join(
                ["Upload-Offset", "Tus-Resumable", "Tus-Upload-Finished"]
            ),
        }

        if self.dm.get("size") is not None and self.dm.get_offset() >= self.dm.get("size"):
            await self.file_storage_manager.finish(self.dm)
            await self.dm.finish()
            headers["Tus-Upload-Finished"] = "1"
        else:
            await self.dm.save()

        return Response(headers=headers)

    async def tus_create(self, *args, **kwargs):
        await self.dm.load()
        # This only happens in tus-java-client, redirect this POST to a PATCH
        if self.request.headers.get("X-HTTP-Method-Override") == "PATCH":
            return await self.tus_patch()

        md5 = extension = size = None

        deferred_length = False
        if self.request.headers.get("Upload-Defer-Length") == "1":
            deferred_length = True

        if "UPLOAD-LENGTH" in self.request.headers:
            size = int(self.request.headers["UPLOAD-LENGTH"])
        else:
            if not deferred_length:
                raise HTTPPreconditionFailed(content={"reason": "We need upload-length header"})

        if "UPLOAD-MD5" in self.request.headers:
            md5 = self.request.headers["UPLOAD-MD5"]

        if "UPLOAD-EXTENSION" in self.request.headers:
            extension = self.request.headers["UPLOAD-EXTENSION"]

        if "TUS-RESUMABLE" not in self.request.headers:
            raise HTTPPreconditionFailed(content={"reason": "TUS needs a TUS version"})

        if "X-UPLOAD-FILENAME" in self.request.headers:
            filename = self.request.headers["X-UPLOAD-FILENAME"]
        elif "UPLOAD-FILENAME" in self.request.headers:
            filename = self.request.headers["UPLOAD-FILENAME"]
        elif "UPLOAD-METADATA" not in self.request.headers:
            filename = uuid.uuid4().hex
        else:
            filename = self.request.headers["UPLOAD-METADATA"]
            filename = base64.b64decode(filename.split()[1]).decode("utf-8")
        if extension is None and "." in filename:
            extension = filename.split(".")[-1]

        await self.dm.start()
        await self.dm.update(
            content_type=self.request.content_type,
            md5=md5,
            filename=filename,
            extension=extension,
            size=size,
            deferred_length=deferred_length,
            offset=0,
        )

        await self.file_storage_manager.start(self.dm)
        await self.dm.save()

        if "filename" in self.request.matchdict:
            location = posixpath.join(
                get_object_url(self.context, self.request),
                "@tusupload",
                self.field.__name__,
                self.request.matchdict["filename"],
            )
        else:
            location = posixpath.join(
                get_object_url(self.context, self.request), "@tusupload", self.field.__name__
            )

        return Response(
            status=201,
            headers={
                "Location": location,  # noqa
                "Tus-Resumable": "1.0.0",
                "Access-Control-Expose-Headers": "Location,Tus-Resumable",
            },
        )

    async def upload(self):
        await self.dm.load()
        md5 = extension = size = None
        if "X-UPLOAD-MD5HASH" in self.request.headers:
            md5 = self.request.headers["X-UPLOAD-MD5HASH"]

        if "X-UPLOAD-EXTENSION" in self.request.headers:
            extension = self.request.headers["X-UPLOAD-EXTENSION"]

        if "X-UPLOAD-SIZE" in self.request.headers:
            size = int(self.request.headers["X-UPLOAD-SIZE"])
        else:
            if "Content-Length" in self.request.headers:
                size = int(self.request.headers["Content-Length"])
            else:  # pragma: no cover
                raise AttributeError("x-upload-size or content-length header needed")

        if "X-UPLOAD-FILENAME" in self.request.headers:
            filename = self.request.headers["X-UPLOAD-FILENAME"]
        elif "X-UPLOAD-FILENAME-B64" in self.request.headers:
            filename = base64.b64decode(self.request.headers["X-UPLOAD-FILENAME-B64"]).decode("utf-8")
        else:
            filename = uuid.uuid4().hex

        await self.dm.start()
        await self.dm.update(
            content_type=self.request.content_type, md5=md5, filename=filename, extension=extension, size=size
        )
        await self.file_storage_manager.start(self.dm)

        read_bytes = await self.file_storage_manager.append(self.dm, self._iterate_request_data(), 0)

        if read_bytes != size:
            raise HTTPPreconditionFailed(content={"reason": "Upload size does not match what was provided"})

        await self.file_storage_manager.finish(self.dm)
        await self.dm.finish()

    async def iter_data(self, *args, **kwargs):
        async for chunk in self.file_storage_manager.iter_data():
            yield chunk

    async def save_file(self, generator, content_type=None, filename=None, extension=None, size=None):
        await self.dm.load()
        await self.dm.start()
        await self.dm.update(
            content_type=content_type, filename=filename or uuid.uuid4().hex, extension=extension, size=size
        )
        await self.file_storage_manager.start(self.dm)

        size = await self.file_storage_manager.append(self.dm, generator(), 0)
        await self.dm.update(size=size)
        await self.file_storage_manager.finish(self.dm)
        return await self.dm.finish()

    async def copy(self, to_manager):
        await to_manager.dm.load()
        await self.file_storage_manager.copy(to_manager.file_storage_manager, to_manager.dm)
