# -*- encoding: utf-8 -*-
from zope.interface import Attribute
from zope.interface import Interface


OID_TYPE = SERIAL_TYPE = bytes


class IBaseObject(Interface):
    """Python base object interface
    """

    _p_jar = Attribute(
        """The data manager for the object.

        The data manager should implement IPersistentDataManager (note that
        this constraint is not enforced).

        If there is no data manager, then this is None.

        Once assigned to a data manager, an object cannot be re-assigned
        to another.
        """)

    _p_oid = Attribute(
        """The object id.

        It is up to the data manager to assign this.

        The special value None is reserved to indicate that an object
        id has not been assigned.  Non-None object ids must be non-empty
        strings.  The int 0 is reserved to identify the
        database root object.

        Once assigned an OID, an object cannot be re-assigned another.
        """)

    _p_changed = Attribute(
        """The persistent state of the object.

        This is one of:

        None -- The object is a ghost.

        false but not None -- The object is saved (or has never been saved).

        true -- The object has been modified since it was last saved.

        The object state may be changed by assigning or deleting this
        attribute; however, assigning None is ignored if the object is
        not in the saved state, and may be ignored even if the object is
        in the saved state.

        At and after ZODB 3.6, setting _p_changed to a true value for a ghost
        object activates the object; prior to 3.6, setting _p_changed to a
        true value on a ghost object was ignored.

        Note that an object can transition to the changed state only if
        it has a data manager.  When such a state change occurs, the
        'register' method of the data manager must be called, passing the
        persistent object.

        Deleting this attribute forces invalidation independent of
        existing state, although it is an error if the sticky state is
        current.
        """)

    _p_serial = Attribute(
        """The object serial number.

        This member is used by the data manager to distiguish distinct
        revisions of a given persistent object.

        This is an 8-byte string (not Unicode).
        """)

    _p_mtime = Attribute(
        """The object's modification time (read-only).

        This is a float, representing seconds since the epoch (as returned
        by time.time).
        """)

    _p_state = Attribute(
        """The object's persistence state token.

        Must be one of GHOST, UPTODATE, CHANGED, or STICKY.
        """)

    _p_estimated_size = Attribute(
        """An estimate of the object's size in bytes.

        May be set by the data manager.
        """)

    # Attribute access protocol
    def __getattribute__(name):
        """ Handle activating ghosts before returning an attribute value.

        "Special" attributes and '_p_*' attributes don't require activation.
        """

    def __setattr__(name, value):
        """ Handle activating ghosts before setting an attribute value.

        "Special" attributes and '_p_*' attributes don't require activation.
        """

    def __delattr__(name):
        """ Handle activating ghosts before deleting an attribute value.

        "Special" attributes and '_p_*' attributes don't require activation.
        """

    # Pickling protocol.
    def __getstate__():
        """Get the object data.

        The state should not include persistent attributes ("_p_name").
        The result must be picklable.
        """

    def __setstate__(state):
        """Set the object data.
        """

    def __reduce__():
        """Reduce an object to contituent parts for serialization.
        """


class IAnnotation(Interface):
    pass