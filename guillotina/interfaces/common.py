from zope.interface import Interface


class IMapping(Interface):
    """Simplest readable mapping object
    """

    def __getitem__(key):  # noqa: N805
        """Get a value for a key

        A KeyError is raised if there is no value for the key.
        """

    def get(key, default=None):  # noqa: N805
        """Get a value for a key

        The default is returned if there is no value for the key.
        """

    def __contains__(key):  # noqa: N805
        """Tell if a key exists in the mapping."""

    def __delitem__(key):  # noqa: N805
        """Delete a value from the mapping using the key."""

    def __setitem__(key, value):  # noqa: N805
        """Set a new item in the mapping."""

    def keys():
        """Return the keys of the mapping object.
        """

    def __iter__():
        """Return an iterator for the keys of the mapping object.
        """

    def values():
        """Return the values of the mapping object.
        """

    def items():
        """Return the items of the mapping object.
        """

    def __len__():
        """Return the number of items.
        """

    def iterkeys():
        'iterate over keys; equivalent to __iter__'

    def itervalues():
        'iterate over values'

    def iteritems():
        'iterate over items'

    def copy():
        'return copy of dict'

    def has_key(key):  # noqa: N805
        """Tell if a key exists in the mapping; equivalent to __contains__"""

    def clear():
        'delete all items'

    def update(d):  # noqa: N805
        ' Update D from E: for k in E.keys(): D[k] = E[k]'

    def setdefault(key, default=None):  # noqa: N805
        'D.setdefault(k[,d]) -> D.get(k,d), also set D[k]=d if k not in D'

    def pop(k, *args):  # noqa: N805
        """remove specified key and return the corresponding value
        *args may contain a single default value, or may not be supplied.
        If key is not found, default is returned if given, otherwise
        KeyError is raised"""

    def popitem():
        """remove and return some (key, value) pair as a
        2-tuple; but raise KeyError if mapping is empty"""
