from guillotina.db import uid
from guillotina.tests import utils


def test_generate_uid():
    ob = utils.create_content()
    assert len(uid.generate_uid(ob)) == uid.UUID_LENGTH  # should just be UUID here


def test_generate_uid_with_parent():
    ob = utils.create_content()
    parent = ob.__parent__ = utils.create_content()
    parent.__parent__ = utils.create_content()
    zoid = uid.generate_uid(ob)
    assert len(zoid) == (uid.UUID_LENGTH + len(uid.OID_DELIMITER) + uid.UID_SPLIT_LENGTH)
    assert zoid.startswith(parent.__uuid__[: uid.UID_SPLIT_LENGTH] + uid.OID_DELIMITER)


def test_generate_uid_with_parents():
    parent = utils.create_content(
        parent=utils.create_content(
            parent=utils.create_content(
                parent=utils.create_content(
                    parent=utils.create_content(
                        parent=utils.create_content(
                            parent=utils.create_content(
                                parent=utils.create_content(
                                    parent=utils.create_content(parent=utils.create_content())
                                )
                            )
                        )
                    )
                )
            )
        )
    )
    ob = utils.create_content(parent=parent)
    zoid = uid.generate_uid(ob)
    assert len(zoid) == uid.MAX_UID_LENGTH
