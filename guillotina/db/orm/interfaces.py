# -*- encoding: utf-8 -*-
from zope.interface import Attribute
from zope.interface import Interface


OID_TYPE = SERIAL_TYPE = bytes


class IBaseObject(Interface):
    """Python base object interface
    """

    __name__ = Attribute("")
    __parent__ = Attribute("")

    __txn__ = Attribute(
        """The data manager for the object.

        The data manager should implement IPersistentDataManager (note that
        this constraint is not enforced).

        If there is no data manager, then this is None.

        Once assigned to a data manager, an object cannot be re-assigned
        to another.
        """
    )

    __uuid__ = Attribute(
        """The object id.

        It is up to the data manager to assign this.

        The special value None is reserved to indicate that an object
        id has not been assigned.  Non-None object ids must be non-empty
        strings.  The int 0 is reserved to identify the
        database root object.

        Once assigned an OID, an object cannot be re-assigned another.
        """
    )

    __serial__ = Attribute(
        """The object serial number.

        This member is used by the data manager to distiguish distinct
        revisions of a given persistent object.

        This is an 8-byte string (not Unicode).
        """
    )

    # Attribute access protocol
    def __getattribute__(name):  # type: ignore
        """
        """

    # Pickling protocol.
    def __getstate__():  # type: ignore
        """Get the object data.

        The state should not include persistent attributes ("_p_name").
        The result must be picklable.
        """

    def register():
        ...
