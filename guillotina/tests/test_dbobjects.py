from guillotina.behaviors.dublincore import IDublinCore
from guillotina.content import Item
from guillotina.interfaces import IAnnotations
from guillotina.transactions import transaction
from guillotina.utils import get_database
from guillotina.content import Item

import pytest


async def test_create_object(guillotina_main):
    async with transaction(db=await get_database("db")) as txn:
        root = await txn.manager.get_root(txn=txn)
        ob1 = Item()
        ob1.type_name = "Item"
        ob1.__new_marker__ = True
        assert ob1.__serial__ is None
        assert ob1.__uuid__ is None
        assert ob1.__parent__ is None
        assert ob1.__of__ is None
        assert ob1.__name__ is None

        await root.async_set("ob1", ob1)

        assert ob1.__name__ == "ob1"
        assert ob1.__uuid__ is not None
        assert ob1.__of__ is None
        assert ob1.__parent__ is root

        assert len(txn.added) == 1


async def test_create_annotation(db):
    async with transaction(db=await get_database("db")) as txn:
        root = await txn.manager.get_root(txn=txn)
        ob1 = Item()
        ob1.type_name = "Item"
        await root.async_set("ob1", ob1)
        annotations = IAnnotations(ob1)
        with pytest.raises(KeyError):
            await annotations.async_set("test", "hola")

        ob2 = Item()
        ob2.type_name = "Item"
        assert ob2.__of__ is None
        assert ob2.__name__ is None
        assert ob2.__parent__ is None
        assert len(ob1.__gannotations__) == 0

        await annotations.async_set("test2", ob2)
        assert ob2.__of__ is ob1.__uuid__
        assert ob2.__name__ == "test2"
        assert ob2.__parent__ is None
        assert len(ob1.__gannotations__) == 1


async def test_use_behavior_annotation(db):
    async with transaction(db=await get_database("db")) as txn:
        root = await txn.manager.get_root(txn=txn)
        ob1 = Item()
        ob1.type_name = "Item"
        await root.async_set("ob1", ob1)
        dublin = IDublinCore(ob1)
        await dublin.load()
        dublin.publisher = "foobar"
        assert dublin.publisher == "foobar"
