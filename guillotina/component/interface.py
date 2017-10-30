from guillotina.component._api import get_component_registry
from zope.interface import alsoProvides
from zope.interface.interfaces import IInterface


def provide_interface(id, interface, iface_type=None, info=''):
    """ Mark 'interface' as a named utilty providing 'iface_type'.
    """
    if not id:
        id = "%s.%s" % (interface.__module__, interface.__name__)

    if not IInterface.providedBy(interface):
        if not isinstance(interface, type):
            raise TypeError(id, "is not an interface or class")
        return

    if iface_type is not None:
        if not iface_type.extends(IInterface):
            raise TypeError(iface_type, "is not an interface type")
        alsoProvides(interface, iface_type)
    else:
        iface_type = IInterface

    registry = get_component_registry()
    registry.registerUtility(interface, iface_type, id, info)
