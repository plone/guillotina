from guillotina.db import oid
from guillotina.tests import utils


def test_generate_oid():
    ob = utils.create_content()
    assert len(oid.generate_oid(ob)) == oid.UUID_LENGTH  # should just be UUID here


def test_generate_oid_with_parent():
    ob = utils.create_content()
    parent = ob.__parent__ = utils.create_content()
    parent.__parent__ = utils.create_content()
    zoid = oid.generate_oid(ob)
    assert len(zoid) == (oid.UUID_LENGTH + len(oid.OID_DELIMITER) + oid.OID_SPLIT_LENGTH)
    assert zoid.startswith(parent._p_oid[:oid.OID_SPLIT_LENGTH] + oid.OID_DELIMITER)


def test_generate_oid_with_parents():
    parent = utils.create_content(
        parent=utils.create_content(
            parent=utils.create_content(
                parent=utils.create_content(
                    parent=utils.create_content(
                        parent=utils.create_content(
                            parent=utils.create_content(
                                parent=utils.create_content(
                                    parent=utils.create_content(
                                        parent=utils.create_content())))))))))
    ob = utils.create_content(parent=parent)
    zoid = oid.generate_oid(ob)
    assert len(zoid) == oid.MAX_OID_LENGTH
