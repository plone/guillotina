from zope.component import getMultiAdapter
from guillotina.db.orm.base import BaseObject
from guillotina.interfaces import IAnnotations, IResourceSerializeToJson
from guillotina.db.transaction import Transaction
from zope.interface import implementer
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.content import Item

from guillotina.interfaces import IResource
import pytest


@implementer(IResource)
class TestObject(BaseObject):
    pass


async def test_create_object(dummy_txn_root):
    async for root in dummy_txn_root:
        assert isinstance(root._p_jar, Transaction)
        assert root._p_jar._tid is None
        ob1 = TestObject()
        assert ob1._p_jar is None
        assert ob1._p_serial is None
        assert ob1._p_oid is None
        assert ob1.__parent__ is None
        assert ob1._p_belongs is None
        assert ob1.__name__ is None

        await root.__setitem__('ob1', ob1)

        assert ob1.__name__ == 'ob1'
        assert ob1._p_jar == root._p_jar
        assert ob1._p_oid is not None
        assert ob1._p_belongs is None
        assert ob1.__parent__ is root

        assert len(ob1._p_jar.added) == 1


async def test_create_annotation(dummy_txn_root):
    async for root in dummy_txn_root:
        ob1 = TestObject()
        await root.__setitem__('ob1', ob1)
        annotations = IAnnotations(ob1)
        with pytest.raises(KeyError):
            await annotations.__setitem__('test', 'hola')

        ob2 = TestObject()
        assert ob2.__of__ is None
        assert ob2._p_jar is None
        assert ob2.__name__ is None
        assert ob2.__parent__ is None
        assert len(ob1.__annotations__) == 0

        await annotations.__setitem__('test2', ob2)
        assert ob2.__of__ is ob1._p_oid
        assert ob2._p_jar is ob1._p_jar
        assert ob2.__name__ == 'test2'
        assert ob2.__parent__ is None
        assert len(ob1.__annotations__) == 1


async def test_use_behavior_annotation(dummy_txn_root):
    async for root in dummy_txn_root:
        ob1 = Item()
        await root.__setitem__('ob1', ob1)
        dublin = IDublinCore(ob1)
        await dublin.__setattr__('publisher', 'foobar')
        value = await dublin.__getattr__('publisher')
        assert value == 'foobar'
