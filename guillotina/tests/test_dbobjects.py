from guillotina.behaviors.dublincore import IDublinCore
from guillotina.content import Item
from guillotina.db.orm.base import BaseObject
from guillotina.db.transaction import Transaction
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IResource
from zope.interface import implementer

import pytest


@implementer(IResource)
class ObjectTest(BaseObject):  # type: ignore
    pass


async def test_create_object(dummy_txn_root):
    async with dummy_txn_root as root:
        assert isinstance(root.__txn__, Transaction)
        ob1 = ObjectTest()
        ob1.__new_marker__ = True
        assert ob1.__txn__ is None
        assert ob1.__serial__ is None
        assert ob1.__uuid__ is None
        assert ob1.__parent__ is None
        assert ob1.__of__ is None
        assert ob1.__name__ is None

        await root.async_set("ob1", ob1)

        assert ob1.__name__ == "ob1"
        assert ob1.__txn__ == root.__txn__
        assert ob1.__uuid__ is not None  # type: ignore
        assert ob1.__of__ is None
        assert ob1.__parent__ is root

        assert len(ob1.__txn__.added) == 1


async def test_create_annotation(dummy_txn_root):
    async with dummy_txn_root as root:
        ob1 = ObjectTest()
        await root.async_set("ob1", ob1)
        annotations = IAnnotations(ob1)
        with pytest.raises(KeyError):
            await annotations.async_set("test", "hola")

        ob2 = ObjectTest()
        assert ob2.__of__ is None
        assert ob2.__txn__ is None
        assert ob2.__name__ is None
        assert ob2.__parent__ is None
        assert len(ob1.__gannotations__) == 0

        await annotations.async_set("test2", ob2)
        assert ob2.__of__ is ob1.__uuid__
        assert ob2.__txn__ is ob1.__txn__
        assert ob2.__name__ == "test2"
        assert ob2.__parent__ is None
        assert len(ob1.__gannotations__) == 1


async def test_use_behavior_annotation(dummy_txn_root):
    async with dummy_txn_root as root:
        ob1 = Item()
        await root.async_set("ob1", ob1)
        dublin = IDublinCore(ob1)
        await dublin.load()
        dublin.publisher = "foobar"
        assert dublin.publisher == "foobar"
