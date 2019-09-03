from guillotina.blob import Blob
from guillotina.content import create_content_in_container
from guillotina.tests.utils import login
from guillotina.transactions import transaction
from guillotina.utils import get_database

import pytest


pytestmark = pytest.mark.asyncio


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
