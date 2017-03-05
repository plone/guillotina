
from guillotina.db.orm.base import BaseObject


def test_create_object():
    ob1 = BaseObject()
    assert ob1._p_jar is None
    assert ob1._p_serial is None