from guillotina import task_vars
from guillotina.behaviors.attachment import IAttachment
from guillotina.behaviors.attachment import IMultiAttachment
from guillotina.component import get_multi_adapter
from guillotina.interfaces import IFileManager
from guillotina.tests import utils
from guillotina.transactions import transaction

import asyncio
import base64
import hashlib
import json
import pytest
import random


_pytest_params = [
    pytest.param("db", marks=pytest.mark.app_settings({"cloud_datamanager": "db"})),
    pytest.param(
        "redis",
        marks=[
            pytest.mark.app_settings(
                {
                    "applications": ["guillotina.contrib.redis"],
                    "cloud_storage": "guillotina.test_package.IMemoryFileField",
                    "cloud_datamanager": "redis",
                }
            )
        ],
    ),
]


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_create_content_with_behavior(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 4,
            headers={"x-upload-size": str(1024 * 1024 * 4)},
        )
        assert status == 200

        response, status = await requester("GET", "/db/guillotina/foobar/@download/file")
        assert status == 200
        assert len(response) == (1024 * 1024 * 4)


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_multi_upload(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {"@type": "Item", "@behaviors": [IMultiAttachment.__identifier__], "id": "foobar"}
            ),
        )
        assert status == 201

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/files/key1",
            data=b"X" * 1024 * 1024 * 10,
            headers={"x-upload-size": str(1024 * 1024 * 10)},
        )
        assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/files/key2",
            data=b"Y" * 1024 * 1024 * 10,
            headers={"x-upload-size": str(1024 * 1024 * 10)},
        )
        assert status == 200

        response, status = await requester("GET", "/db/guillotina/foobar/@download/files/key1")
        assert status == 200
        assert response == b"X" * 1024 * 1024 * 10

        response, status = await requester("GET", "/db/guillotina/foobar/@download/files/key2")
        assert status == 200
        assert response == b"Y" * 1024 * 1024 * 10

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("foobar")
            behavior = IMultiAttachment(obj)
            await behavior.load()
            assert behavior.files["key1"].chunks == 2
            assert behavior.files["key2"].chunks == 2


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_large_upload_chunks(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 10,
            headers={"x-upload-size": str(1024 * 1024 * 10)},
        )
        assert status == 200

        response, status = await requester("GET", "/db/guillotina/foobar/@download/file")
        assert status == 200
        assert len(response) == (1024 * 1024 * 10)

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("foobar")
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file.chunks == 2


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_tus(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "OPTIONS",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Origin": "http://foobar.com", "Access-Control-Request-Method": "POST"},
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"UPLOAD-LENGTH": str(1024 * 1024 * 10), "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        response, status = await requester("HEAD", "/db/guillotina/foobar/@tusupload/file")
        assert status == 200

        for idx in range(10):
            # 10, 1mb chunks
            response, status = await requester(
                "PATCH",
                "/db/guillotina/foobar/@tusupload/file",
                headers={
                    "CONTENT-LENGTH": str(1024 * 1024 * 1),
                    "TUS-RESUMABLE": "1.0.0",
                    "upload-offset": str(1024 * 1024 * idx),
                },
                data=b"X" * 1024 * 1024 * 1,
            )
            assert status == 200

        response, status = await requester("GET", "/db/guillotina/foobar/@download/file")
        assert status == 200
        assert len(response) == (1024 * 1024 * 10)

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("foobar")
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file.chunks == 10


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_tus_multi(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {"@type": "Item", "@behaviors": [IMultiAttachment.__identifier__], "id": "foobar"}
            ),
        )
        assert status == 201

        response, status = await requester(
            "OPTIONS",
            "/db/guillotina/foobar/@tusupload/files/file",
            headers={"Origin": "http://foobar.com", "Access-Control-Request-Method": "POST"},
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/files/file",
            headers={"UPLOAD-LENGTH": str(1024 * 1024 * 10), "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        response, status = await requester("HEAD", "/db/guillotina/foobar/@tusupload/files/file")
        assert status == 200

        for idx in range(10):
            # 10, 1mb chunks
            response, status = await requester(
                "PATCH",
                "/db/guillotina/foobar/@tusupload/files/file",
                headers={
                    "CONTENT-LENGTH": str(1024 * 1024 * 1),
                    "TUS-RESUMABLE": "1.0.0",
                    "upload-offset": str(1024 * 1024 * idx),
                },
                data=b"X" * 1024 * 1024 * 1,
            )
            assert status == 200

        response, status = await requester("GET", "/db/guillotina/foobar/@download/files/file")
        assert status == 200
        assert len(response) == (1024 * 1024 * 10)

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("foobar")
            behavior = IMultiAttachment(obj)
            await behavior.load()
            assert behavior.files["file"].chunks == 10


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_tus_unknown_size(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "OPTIONS",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Origin": "http://foobar.com", "Access-Control-Request-Method": "POST"},
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Upload-Defer-Length": "1", "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        response, status = await requester("HEAD", "/db/guillotina/foobar/@tusupload/file")
        assert status == 200

        offset = 0
        for idx in range(10):
            # random sizes
            size = 1024 * random.choice([1024, 1243, 5555, 7777])
            response, status = await requester(
                "PATCH",
                "/db/guillotina/foobar/@tusupload/file",
                headers={"TUS-RESUMABLE": "1.0.0", "upload-offset": str(offset)},
                data=b"X" * size,
            )
            offset += size
            assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@tusupload/file",
            headers={
                "TUS-RESUMABLE": "1.0.0",
                "upload-offset": str(offset),
                "UPLOAD-LENGTH": str(offset),  # finish it
            },
            data=b"",
        )

        response, status = await requester("GET", "/db/guillotina/foobar/@download/file")
        assert status == 200
        assert len(response) == offset

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("foobar")
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file.size == offset


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_copy_file_ob(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201
        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 4,
            headers={"x-upload-size": str(1024 * 1024 * 4)},
        )
        assert status == 200

        async with transaction(db=requester.db, abort_when_done=True) as txn:
            root = await txn.manager.get_root(txn)
            container = await root.async_get("guillotina")
            task_vars.container.set(container)
            request = utils.get_mocked_request(db=requester.db)
            with request:
                obj = await container.async_get("foobar")
                attachment = IAttachment(obj)
                await attachment.load()
                if manager_type == "db":
                    existing_id = attachment.file._blob.bid
                else:
                    existing_id = attachment.file.uri
                cfm = get_multi_adapter((obj, request, IAttachment["file"].bind(attachment)), IFileManager)
                from_cfm = get_multi_adapter(
                    (obj, request, IAttachment["file"].bind(attachment)), IFileManager
                )
                await cfm.copy(from_cfm)
                if manager_type == "db":
                    assert existing_id != attachment.file._blob.bid
                else:
                    assert existing_id != attachment.file.uri


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_tus_unfinished_error(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "OPTIONS",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Origin": "http://foobar.com", "Access-Control-Request-Method": "POST"},
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Upload-Length": "1024", "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Upload-Length": "1024", "TUS-RESUMABLE": "1.0.0"},
        )
        # upload already started, should error
        assert status == 412

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Upload-Length": "1024", "TUS-RESUMABLE": "1.0.0", "TUS-OVERRIDE-UPLOAD": "1"},
        )
        # override it
        assert status == 201


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_tus_with_empty_file(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "OPTIONS",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"Origin": "http://foobar.com", "Access-Control-Request-Method": "POST"},
        )
        assert status == 200

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"UPLOAD-LENGTH": "0", "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        response, status = await requester("HEAD", "/db/guillotina/foobar/@tusupload/file")
        assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"CONTENT-LENGTH": "0", "TUS-RESUMABLE": "1.0.0", "upload-offset": "0"},
            data=b"",
        )
        assert status == 200

        response, status = await requester("GET", "/db/guillotina/foobar/@download/file")
        assert status == 200
        assert len(response) == 0

        root = await utils.get_root(db=requester.db)
        async with transaction(db=requester.db, abort_when_done=True):
            container = await root.async_get("guillotina")
            obj = await container.async_get("foobar")
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file.chunks == 0


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_update_filename_on_files_on_post(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        data = "WFhY" * 1024 + "WA=="
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps(
                {
                    "@type": "Item",
                    "@behaviors": [IAttachment.__identifier__],
                    "id": "foobar",
                    IAttachment.__identifier__: {
                        "file": {
                            "filename": "foobar.jpg",
                            "content-type": "image/jpeg",
                            "encoding": "base64",
                            "data": data,
                        }
                    },
                }
            ),
        )
        assert status == 201

        response, status = await requester("GET", "/db/guillotina/foobar")
        data = response[IAttachment.__identifier__]["file"]
        assert data["filename"] == "foobar.jpg"
        assert data["content_type"] == "image/jpeg"

        response, status = await requester("GET", "/db/guillotina/foobar/@download/file")
        assert len(response) == 3073


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_update_filename_on_files(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024,
            headers={"x-upload-size": str(1024 * 1024)},
        )
        assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar",
            data=json.dumps(
                {
                    IAttachment.__identifier__: {
                        "file": {
                            "filename": "foobar.jpg",
                            "content_type": "image/jpeg",
                            "md5": "foobar",
                            "extension": "jpg",
                        }
                    }
                }
            ),
        )

        response, status = await requester("GET", "/db/guillotina/foobar")
        data = response[IAttachment.__identifier__]["file"]
        assert data["filename"] == "foobar.jpg"
        assert data["content_type"] == "image/jpeg"
        assert data["md5"] == "foobar"
        assert data["extension"] == "jpg"


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_should_fourohfour_with_invalid_fieldname(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester("GET", "/db/guillotina/foobar/@download/foobar")
        assert status == 404


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_file_head(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201
        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 4,
            headers={"x-upload-size": str(1024 * 1024 * 4)},
        )
        assert status == 200

        response, status, headers = await requester.make_request(
            "HEAD", "/db/guillotina/foobar/@download/file"
        )
        assert status == 200
        assert headers["Content-Length"] == str(1024 * 1024 * 4)
        assert headers["Content-Type"] == "application/octet-stream"
        assert headers["Accept-Ranges"] == "bytes"


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_file_head_not_found(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        _, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status, headers = await requester.make_request(
            "HEAD", "/db/guillotina/foobar/@download/file", accept="application/json"
        )
        assert status == 404


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_range_request_download(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"UPLOAD-LENGTH": str(1024 * 1024 * 10), "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        for idx in range(10):
            # 10, 1mb chunks
            response, status = await requester(
                "PATCH",
                "/db/guillotina/foobar/@tusupload/file",
                headers={
                    "CONTENT-LENGTH": str(1024 * 1024 * 1),
                    "TUS-RESUMABLE": "1.0.0",
                    "upload-offset": str(1024 * 1024 * idx),
                },
                data=str(idx).encode("ascii") * 1024 * 1024 * 1,
            )
            assert status == 200

        response, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/foobar/@download/file",
            accept="application/json",
            headers={"Range": f"bytes={1024 * 1024}-{(2 * 1024 * 1024) - 1}"},
        )

        assert headers["Content-Range"] == f"bytes {1024 * 1024}-{(2 * 1024 * 1024) - 1}/{10 * 1024 * 1024}"
        assert len(response) == 1024 * 1024
        assert response == b"1" * 1024 * 1024

        response, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/foobar/@download/file",
            headers={"Range": f"bytes={(1024 * 1024 * 3) + 512}-{((5 * 1024 * 1024) + 512) - 1}"},
        )

        assert len(response) == 2 * 1024 * 1024
        assert response == (b"3" * ((1024 * 1024) - 512)) + (b"4" * 1024 * 1024) + (b"5" * 512)

        # test whole range
        response, status, headers = await requester.make_request(
            "GET",
            "/db/guillotina/foobar/@download/file",
            accept="application/json",
            headers={"Range": f"bytes=0-"},
        )

        assert headers["Content-Range"] == f"bytes 0-{(10 * 1024 * 1024) - 1}/{10 * 1024 * 1024}"
        assert len(response) == 10 * 1024 * 1024


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_invalid_range_request_download(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"UPLOAD-LENGTH": str(1024 * 1024 * 2), "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        for idx in range(2):
            # 2, 1mb chunks
            response, status = await requester(
                "PATCH",
                "/db/guillotina/foobar/@tusupload/file",
                headers={
                    "CONTENT-LENGTH": str(1024 * 1024 * 1),
                    "TUS-RESUMABLE": "1.0.0",
                    "upload-offset": str(1024 * 1024 * idx),
                },
                data=str(idx).encode("ascii") * 1024 * 1024 * 1,
            )
            assert status == 200

        _, status, _ = await requester.make_request(
            "GET", "/db/guillotina/foobar/@download/file", headers={"Range": f"foobar=0-2"}
        )
        assert status == 416

        _, status, _ = await requester.make_request(
            "GET", "/db/guillotina/foobar/@download/file", headers={"Range": f"bytes=zero-2"}
        )
        assert status == 416

        _, status, _ = await requester.make_request(
            "GET", "/db/guillotina/foobar/@download/file", headers={"Range": f"bytes=5-2"}
        )
        assert status == 416

        _, status, _ = await requester.make_request(
            "GET",
            "/db/guillotina/foobar/@download/file",
            headers={"Range": f"bytes={(1024 * 1024 * 5)}-{(1024 * 1024 * 7)}"},
        )
        assert status == 416


@pytest.mark.parametrize("manager_type", _pytest_params)
async def _test_handle_cancel_error(manager_type, redis_container, container_requester):  # pragma: no cover
    # it seems we can't test cancelled errors with pytest
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"UPLOAD-LENGTH": str(1024 * 1024 * 3), "TUS-RESUMABLE": "1.0.0"},
        )
        assert status == 201

        for idx in range(3):
            # 10, 1mb chunks
            response, status = await requester(
                "PATCH",
                "/db/guillotina/foobar/@tusupload/file",
                headers={
                    "CONTENT-LENGTH": str(1024 * 1024 * 1),
                    "TUS-RESUMABLE": "1.0.0",
                    "upload-offset": str(1024 * 1024 * idx),
                },
                data=str(idx).encode("ascii") * 1024 * 1024 * 1,
            )
            assert status == 200

        task = asyncio.create_task(
            requester.make_request(
                "GET",
                "/db/guillotina/foobar/@download/file",
                accept="application/json",
                headers={"Range": f"bytes=0-"},
            )
        )
        await asyncio.sleep(0.005)
        task.cancel()
        _, status, _ = await task


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_tus_errors(manager_type, redis_container, container_requester):
    # it seems we can't test cancelled errors with pytest
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "POST", "/db/guillotina/foobar/@tusupload/file", headers={"UPLOAD-LENGTH": str(1024 * 1024 * 3)}
        )
        assert status == 412

        response, status = await requester(
            "POST", "/db/guillotina/foobar/@tusupload/file", headers={"TUS-RESUMABLE": "1.0.0"}
        )
        assert status == 412

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={
                "UPLOAD-LENGTH": str(1024 * 1024 * 3),
                "TUS-RESUMABLE": "1.0.0",
                "UPLOAD-MD5": hashlib.md5(b"0" * 1024 * 1024 * 3).hexdigest(),
                "UPLOAD-EXTENSION": "jpg",
                "X-UPLOAD-FILENAME": "foobar.jpg",
            },
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={
                "UPLOAD-LENGTH": str(1024 * 1024 * 3),
                "TUS-RESUMABLE": "1.0.0",
                "UPLOAD-FILENAME": "foobar.jpg",
                "TUS-OVERRIDE-UPLOAD": "1",
            },
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={
                "UPLOAD-LENGTH": str(1024 * 1024 * 3),
                "TUS-RESUMABLE": "1.0.0",
                "UPLOAD-METADATA": "foo " + base64.b64encode(b"foobar.jpg").decode("utf-8"),
                "TUS-OVERRIDE-UPLOAD": "1",
            },
        )
        assert status == 201

        response, status = await requester(
            "POST",
            "/db/guillotina/foobar/@tusupload/file",
            headers={
                "CONTENT-LENGTH": str(1024 * 1024 * 1),
                "TUS-RESUMABLE": "1.0.0",
                "X-HTTP-Method-Override": "PATCH",
            },
            data=b"0" * 1024 * 1024 * 1,
        )
        assert status == 412

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"CONTENT-LENGTH": str(1024 * 1024 * 1), "TUS-RESUMABLE": "1.0.0", "upload-offset": "0"},
            data=b"0" * 1024 * 1024 * 1,
        )
        assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@tusupload/file",
            headers={"CONTENT-LENGTH": str(1024 * 1024 * 1), "TUS-RESUMABLE": "1.0.0", "upload-offset": "0"},
            data=b"1" * 1024 * 1024 * 1,
        )
        assert status == 409


@pytest.mark.parametrize("manager_type", _pytest_params)
async def test_upload_errors(manager_type, redis_container, container_requester):
    async with container_requester as requester:
        response, status = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "@behaviors": [IAttachment.__identifier__], "id": "foobar"}),
        )
        assert status == 201

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 4,
            headers={
                "content-length": str(1024 * 1024 * 4),
                "X-UPLOAD-MD5HASH": hashlib.md5(b"X" * 1024 * 1024 * 4).hexdigest(),
                "X-UPLOAD-EXTENSION": "bin",
                "X-UPLOAD-FILENAME": "foo.bin",
            },
        )
        assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 4,
            headers={
                "content-length": str(1024 * 1024 * 4),
                "UPLOAD-MD5": hashlib.md5(b"X" * 1024 * 1024 * 4).hexdigest(),
                "X-UPLOAD-EXTENSION": "bin",
                "X-UPLOAD-FILENAME-B64": base64.b64encode(b"foobar.bin").decode("utf-8"),
            },
        )
        assert status == 200

        response, status = await requester(
            "PATCH",
            "/db/guillotina/foobar/@upload/file",
            data=b"X" * 1024 * 1024 * 4,
            headers={
                "x-upload-size": str(1024 * 1024 * 1),
                "UPLOAD-MD5": hashlib.md5(b"X" * 1024 * 1024 * 4).hexdigest(),
                "X-UPLOAD-EXTENSION": "bin",
                "X-UPLOAD-FILENAME-B64": base64.b64encode(b"foobar.bin").decode("utf-8"),
            },
        )
        assert status == 412
