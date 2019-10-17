from guillotina.content import create_content_in_container
from guillotina.fields.annotation import BucketDictValue
from guillotina.tests.utils import login
from guillotina.transactions import transaction
from guillotina.utils import get_database

import os
import pytest


pytest.mark.skipif(os.environ.get("DATABASE") == "cockroachdb", reason="Flaky cockroachdb test")


async def test_bucket_dict_value(db, guillotina_main):
    db = await get_database("db")
    login()
    bucket = BucketDictValue(bucket_len=10)

    async with transaction(db=db):
        container = await create_content_in_container(db, "Container", "container", title="Container")
        ob = await create_content_in_container(container, "Item", "foobar")
        for index in range(50):
            await bucket.assign(ob, str(index), index)

        assert len(bucket) == 50
        assert await bucket.get(ob, "1") == 1

    async with transaction(db=db):
        container = await db.async_get("container")
        ob = await container.async_get("foobar")
        await bucket.clear(ob)
        assert len(bucket) == 0
        assert await bucket.get(ob, "1") == None

    async with transaction(db=db):
        container = await db.async_get("container")
        ob = await container.async_get("foobar")
        total = 100
        for index in range(50, 100):
            await bucket.assign(ob, str(index), index)

        assert len(bucket) == 50
        assert await bucket.get(ob, "50") == 50
