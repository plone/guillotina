from guillotina.behaviors.attachment import IAttachment
from guillotina.blob import Blob
from guillotina.component import get_multi_adapter
from guillotina.content import create_content_in_container
from guillotina.exceptions import BlobChunkNotFound
from guillotina.files.exceptions import RangeNotFound
from guillotina.files.exceptions import RangeNotSupported
from guillotina.interfaces import IFileManager
from guillotina.tests.utils import login
from guillotina.transactions import transaction
from guillotina.utils import get_behavior
from guillotina.utils import get_database

import pytest


async def test_create_blob(db, guillotina_main):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await create_content_in_container(db, "Container", "container", title="Container")

        blob = Blob(container)
        container.blob = blob

    async with transaction(db=db):
        container = await db.async_get("container")
        assert blob.bid == container.blob.bid
        assert blob.resource_uid == container.__uuid__
        await db.async_del("container")


async def test_write_blob_data(db, guillotina_main):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await db.async_get("container")
        if container is None:
            container = await create_content_in_container(db, "Container", "container", title="Container")

        blob = Blob(container)
        container.blob = blob

        blobfi = blob.open("w")
        await blobfi.async_write(b"foobar")

    async with transaction(db=db):
        container = await db.async_get("container")
        assert await container.blob.open().async_read() == b"foobar"
        assert container.blob.size == 6
        assert container.blob.chunks == 1

        await db.async_del("container")


async def test_open_blob_error(db, guillotina_main):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await db.async_get("container")
        if container is None:
            container = await create_content_in_container(db, "Container", "container", title="Container")

        blob = Blob(container)
        with pytest.raises(Exception):
            bf = blob.open("X")
            await bf.async_write_chunk(b"")
        with pytest.raises(BlobChunkNotFound):
            bf = blob.open()
            await bf.async_read_chunk(1)


async def test_write_large_blob_data(db, guillotina_main):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await db.async_get("container")
        if container is None:
            container = await create_content_in_container(db, "Container", "container", title="Container")

        blob = Blob(container)
        container.blob = blob

        multiplier = 999999

        blobfi = blob.open("w")
        await blobfi.async_write(b"foobar" * multiplier)

    async with transaction(db=db):
        container = await db.async_get("container")
        assert await container.blob.open().async_read() == (b"foobar" * multiplier)
        assert container.blob.size == len(b"foobar" * multiplier)
        assert container.blob.chunks == 6

        await db.async_del("container")


async def _gather_all(iterator):
    data = b""
    async for v in iterator:
        data += v
    return data


async def test_read_data_ranges(db, guillotina_main, dummy_request):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await db.async_get("container")
        if container is None:
            container = await create_content_in_container(db, "Container", "container", title="Container")

        container.add_behavior(IAttachment)
        beh = await get_behavior(container, IAttachment, create=True)

        fm = get_multi_adapter((container, dummy_request, IAttachment["file"].bind(beh)), IFileManager)

        async def file_generator():
            yield (b"X" * (1024 * 1024 * 1)) + (b"Y" * 512)
            yield b"Z" * (1024 * 1024 * 10)

        await fm.save_file(file_generator)

    async with transaction(db=db):
        container = await db.async_get("container")
        container.add_behavior(IAttachment)
        beh = await get_behavior(container, IAttachment)
        fm = get_multi_adapter((container, dummy_request, IAttachment["file"].bind(beh)), IFileManager)
        data = b""
        async for chunk in fm.iter_data():
            data += chunk
        assert len(data) == ((1024 * 1024 * 11) + 512)

        assert await fm.file_storage_manager.range_supported()

        assert await _gather_all(fm.file_storage_manager.read_range(0, 1024 * 1024)) == b"X" * 1024 * 1024
        assert (
            await _gather_all(fm.file_storage_manager.read_range(1024 * 1024, (1024 * 1024) + 512))
            == b"Y" * 512
        )
        assert await _gather_all(fm.file_storage_manager.read_range(1024 * 1023, (1024 * 1024) + 1024)) == (
            b"X" * 1024
        ) + (b"Y" * 512) + (b"Z" * 512)
        assert await _gather_all(fm.file_storage_manager.read_range(0, (1024 * 1024 * 11) + 512)) == (
            b"X" * (1024 * 1024 * 1)
        ) + (b"Y" * 512) + (b"Z" * (1024 * 1024 * 10))


async def test_read_data_range_errors(db, guillotina_main, dummy_request):
    db = await get_database("db")
    login()

    async with transaction(db=db):
        container = await db.async_get("container")
        if container is None:
            container = await create_content_in_container(db, "Container", "container", title="Container")

        container.add_behavior(IAttachment)
        beh = await get_behavior(container, IAttachment, create=True)

        fm = get_multi_adapter((container, dummy_request, IAttachment["file"].bind(beh)), IFileManager)

        with pytest.raises(RangeNotSupported):
            # raise before we've added anything
            async for c in fm.file_storage_manager.read_range(1, 2):
                ...  # pragma: no cover

        async def file_generator():
            yield (b"X" * (1024 * 1024 * 1))

        await fm.save_file(file_generator)

    async with transaction(db=db):
        container = await db.async_get("container")
        container.add_behavior(IAttachment)
        beh = await get_behavior(container, IAttachment)
        fm = get_multi_adapter((container, dummy_request, IAttachment["file"].bind(beh)), IFileManager)

        with pytest.raises(RangeNotFound):
            assert await _gather_all(fm.file_storage_manager.read_range(0, 1024 * 1024 * 3))
