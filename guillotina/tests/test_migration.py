from guillotina.migrations import migrate_tags
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.interfaces import IAnnotationData
from guillotina.content import create_content
from guillotina.transactions import transaction
from guillotina.utils import get_behavior
from guillotina.utils import get_database
from guillotina.utils import get_object_by_oid
from guillotina.tests import utils
import pytest


pytestmark = pytest.mark.asyncio


async def test_migration_600a1(container_requester):
    async with container_requester as requester:
        async with requester.db.get_transaction_manager().transaction():
            container = await requester.db.async_get('guillotina')
            bhr = await get_behavior(container, IDublinCore, create=True)
            key = bhr.__dict__["prefix"] + "tags"
            data = bhr.__dict__["data"]
            data[key] = ["MyTag1", "MyTag2"]
            if IAnnotationData.providedBy(data):
                data.register()
            assert bhr.tags is None

        async with requester.db.get_transaction_manager().transaction():
            await migrate_tags(requester.db)

        async with requester.db.get_transaction_manager().transaction():
            container = await requester.db.async_get('guillotina')
            bhr = await get_behavior(container, IDublinCore)
            assert bhr.tags == ['MyTag1', 'MyTag2']
