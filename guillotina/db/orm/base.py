from guillotina.db.orm.interfaces import IBaseObject
from sys import intern
from zope.interface import implementer

import copyreg


GHOST = -1
ROOT = 0
FULL = 1
CHANGED = 1
UPTODATE = 2

# Bitwise flags
_CHANGED = 0x0001
_STICKY = 0x0002

_OGA = object.__getattribute__
_OSA = object.__setattr__

# These names can be used from a ghost without causing it to be
# activated. These are standardized with the C implementation
SPECIAL_NAMES = ('__class__',
                 '__del__',
                 '__dict__',
                 '__of__',
                 '__setstate__',)

# And this is an implementation detail of this class; it holds
# the standard names plus the slot names, allowing for just one
# check in __getattribute__
_SPECIAL_NAMES = set(SPECIAL_NAMES)


"""
A Base object can be connected to :

+ Tree object : It has a __parent and a __name

+ Annotation object :
    + It belongs to a tree object, its id is the key on the __annotation meta dictionary
    + The pointer to the tree object is __belongs

"""


@implementer(IBaseObject)
class BaseObject(object):
    """ Pure Python implmentation of Persistent base class
    """

    # This slots are NOT going to be on the serialization on the DB
    __slots__ = (
        '__jar', '__oid', '__serial', '__flags', '__size',
        '__of', '__parent', '__annotations', '__name', '__cache')

    def __new__(cls, *args, **kw):
        inst = super(BaseObject, cls).__new__(cls)
        _OSA(inst, '_BaseObject__jar', None)
        _OSA(inst, '_BaseObject__oid', None)
        _OSA(inst, '_BaseObject__serial', None)
        _OSA(inst, '_BaseObject__flags', CHANGED)  # start with changed...
        _OSA(inst, '_BaseObject__size', 0)
        _OSA(inst, '_BaseObject__of', None)
        _OSA(inst, '_BaseObject__parent', None)
        _OSA(inst, '_BaseObject__name', None)
        _OSA(inst, '_BaseObject__annotations', {})
        _OSA(inst, '_BaseObject__cache', -1)
        return inst

    def __repr__(self):
        return "<%s %d>" % (self.__class__.__name__, id(self))

    def _get_parent(self):
        parent = _OGA(self, '_BaseObject__parent')
        if parent is None:
            return None
        if not isinstance(parent, int):
            return parent
        jar = _OGA(self, '_BaseObject__jar')
        if jar is None:
            raise Exception('No JAR and has a parent, impossible')
        oid = _OGA(self, '_BaseObject__oid')
        if oid is None:
            raise Exception('No OID')
        # await jar.get_parent(oid)

    def _set_parent(self, value):
        _OSA(self, '_BaseObject__parent', value)

    def _del_parent(self):
        _OSA(self, '_BaseObject__parent', None)

    __parent__ = property(_get_parent, _set_parent, _del_parent)

    def _get_of(self):
        # should be set when attribute is set...
        return _OGA(self, '_BaseObject__of')

    def _set_of(self, value):
        _OSA(self, '_BaseObject__of', value)

    def _del_of(self):
        _OSA(self, '_BaseObject__of', None)

    __of__ = property(_get_of, _set_of, _del_of)

    # _p_jar:  romantic name of the global connection obj.
    def _get_jar(self):
        return _OGA(self, '_BaseObject__jar')

    def _set_jar(self, value):
        _OSA(self, '_BaseObject__jar', value)

    def _del_jar(self):
        _OSA(self, '_BaseObject__jar', None)

    _p_jar = property(_get_jar, _set_jar, _del_jar)

    # _p_oid:  Identifier of the object.
    def _get_oid(self):
        return _OGA(self, '_BaseObject__oid')

    def _set_oid(self, value):
        _OSA(self, '_BaseObject__oid', value)

    def _del_oid(self):
        _OSA(self, '_BaseObject__oid', None)

    _p_oid = property(_get_oid, _set_oid, _del_oid)

    # _p_serial:  serial number.
    def _get_serial(self):
        return _OGA(self, '_BaseObject__serial')

    def _set_serial(self, value):
        _OSA(self, '_BaseObject__serial', value)

    def _del_serial(self):
        _OSA(self, '_BaseObject__serial', None)

    _p_serial = property(_get_serial, _set_serial, _del_serial)

    # _p_state
    def _get_state(self):
        # Note the use of OGA and caching to avoid recursive calls to __getattribute__:
        # __getattribute__ calls _p_accessed calls cache.mru() calls _p_state
        if _OGA(self, '_BaseObject__jar') is None:
            return UPTODATE
        flags = _OGA(self, '_BaseObject__flags')
        if flags is None:
            return GHOST
        if flags & _CHANGED:
            result = CHANGED
        else:
            result = UPTODATE
        return result

    _p_state = property(_get_state)

    # The '_p_status' property is not (yet) part of the API:  for now,
    # it exists to simplify debugging and testing assertions.
    def _get_status(self):
        if _OGA(self, '_BaseObject__jar') is None:
            return 'unsaved'
        flags = _OGA(self, '_BaseObject__flags')
        if flags is None:
            return 'ghost'
        if flags & _STICKY:
            return 'sticky'
        if flags & _CHANGED:
            return 'changed'
        return 'saved'

    _p_status = property(_get_status)

    def __setattr__(self, name, value):
        special_name = (name in _SPECIAL_NAMES or
                        name.startswith('_p_'))
        volatile = name.startswith('_v_')
        _OSA(self, name, value)
        if (_OGA(self, '_BaseObject__jar') is not None and
                _OGA(self, '_BaseObject__oid') is not None and
                not special_name and
                not volatile):
            before = _OGA(self, '_BaseObject__flags')
            after = before | _CHANGED
            if before != after:
                _OSA(self, '_BaseObject__flags', after)
                _OGA(self, '_p_register')()

    def _slotnames(self):
        """Returns all the slot names from the object"""
        slotnames = copyreg._slotnames(type(self))
        return [
            x for x in slotnames
            if not x.startswith('_p_') and
            not x.startswith('_v_') and
            not x.startswith('_BaseObject__') and
            x not in BaseObject.__slots__]

    def __getstate__(self):
        """ See IPersistent.
        """
        idict = getattr(self, '__dict__', None)
        slotnames = self._slotnames()
        if idict is not None:
            d = dict([x for x in idict.items()
                      if not x[0].startswith('_p_') and not x[0].startswith('_v_')])
        else:
            d = None
        if slotnames:
            s = {}
            for slotname in slotnames:
                value = getattr(self, slotname, self)
                if value is not self:
                    s[slotname] = value
            return d, s
        return d

    def __setstate__(self, state):
        """ See IPersistent.
        """
        if isinstance(state, tuple):
            inst_dict, slots = state
        else:
            inst_dict, slots = state, ()
        idict = getattr(self, '__dict__', None)
        if inst_dict is not None:
            if idict is None:
                raise TypeError('No instance dict')
            idict.clear()
            for k, v in inst_dict.items():
                # Normally the keys for instance attributes are interned.
                # Do that here, but only if it is possible to do so.
                idict[intern(k) if type(k) is str else k] = v
        slotnames = self._slotnames()
        if slotnames:
            for k, v in slots.items():
                setattr(self, k, v)

    def __reduce__(self):
        """ See IPersistent.
        """
        gna = getattr(self, '__getnewargs__', lambda: ())
        return (copyreg.__newobj__,
                (type(self),) + gna(), self.__getstate__())

    def _p_register(self):
        jar = _OGA(self, '_BaseObject__jar')
        if jar is not None:
            jar.register(self)

    def _p_unregister(self):
        jar = _OGA(self, '_BaseObject__jar')
        if jar is not None and _OGA(self, '_BaseObject__oid') is not None:
            jar.unregister(self)

    def _get_name(self):
        return _OGA(self, '_BaseObject__name')

    def _set_name(self, value):
        return _OSA(self, '_BaseObject__name', value)

    def _del_name(self):
        return _OSA(self, '_BaseObject__name', None)

    __name__ = property(_get_name, _set_name, _del_name)

    def _get_annotation(self):
        return _OGA(self, '_BaseObject__annotations')

    def _set_annotation(self, value):
        _OSA(self, '_BaseObject__annotations', value)

    def _del_annotation(self):
        return _OSA(self, '_BaseObject__annotations', None)

    __annotations__ = property(_get_annotation, _set_annotation, _del_annotation)

    # CACHE
    # -1 : No cache
    # 0 : Allways
    # X : ttl

    def _get_cache(self):
        return _OGA(self, '_BaseObject__cache')

    def _set_cache(self, value):
        _OSA(self, '_BaseObject__cache', value)

    def _del_cache(self):
        return _OSA(self, '_BaseObject__cache', None)

    __cache__ = property(_get_cache, _set_cache, _del_cache)
