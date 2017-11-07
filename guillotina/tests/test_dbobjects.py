from guillotina.behaviors.dublincore import IDublinCore
from guillotina.content import Item
from guillotina.db.orm.base import BaseObject
from guillotina.db.transaction import Transaction
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IResource
from zope.interface import implementer

import pytest


@implementer(IResource)
class ObjectTest(BaseObject):
    pass


async def test_create_object(dummy_txn_root):
    async with dummy_txn_root as root:
        assert isinstance(root._p_jar, Transaction)
        ob1 = ObjectTest()
        ob1.__new_marker__ = True
        assert ob1._p_jar is None
        assert ob1._p_serial is None
        assert ob1._p_oid is None
        assert ob1.__parent__ is None
        assert ob1.__of__ is None
        assert ob1.__name__ is None

        await root.async_set('ob1', ob1)

        assert ob1.__name__ == 'ob1'
        assert ob1._p_jar == root._p_jar
        assert ob1._p_oid is not None
        assert ob1.__of__ is None
        assert ob1.__parent__ is root

        assert len(ob1._p_jar.added) == 1


async def test_create_annotation(dummy_txn_root):
    async with dummy_txn_root as root:
        ob1 = ObjectTest()
        await root.async_set('ob1', ob1)
        annotations = IAnnotations(ob1)
        with pytest.raises(KeyError):
            await annotations.async_set('test', 'hola')

        ob2 = ObjectTest()
        assert ob2.__of__ is None
        assert ob2._p_jar is None
        assert ob2.__name__ is None
        assert ob2.__parent__ is None
        assert len(ob1.__annotations__) == 0

        await annotations.async_set('test2', ob2)
        assert ob2.__of__ is ob1._p_oid
        assert ob2._p_jar is ob1._p_jar
        assert ob2.__name__ == 'test2'
        assert ob2.__parent__ is None
        assert len(ob1.__annotations__) == 1


async def test_use_behavior_annotation(dummy_txn_root):
    async with dummy_txn_root as root:
        ob1 = Item()
        await root.async_set('ob1', ob1)
        dublin = IDublinCore(ob1)
        await dublin.load()
        dublin.publisher = 'foobar'
        assert dublin.publisher == 'foobar'
