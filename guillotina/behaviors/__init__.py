# so we can scan guillotina.behaviors and load behavior configuration
from . import attachment  # noqa
from . import dublincore  # noqa
from . import dynamic  # noqa
from guillotina.component import get_utilities_for
from guillotina.component import get_utility
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IResourceFactory
from guillotina.profile import profilable
from zope.interface import alsoProvides
from zope.interface import classImplements


def apply_concrete_behaviors():
    '''
    Configured behaviors for an object should always be applied and can't
    be removed.

    Should be called once at startup instead of doing alsoProvides every
    time an object is created
    '''
    for type_name, factory in get_utilities_for(IResourceFactory):
        for behavior in factory.behaviors:
            behavior_registration = get_utility(
                IBehavior, name=behavior.__identifier__)
            if behavior_registration.marker is not None:
                classImplements(factory._callable, behavior_registration.marker)

@profilable
def apply_markers(obj, event=None):
    """Event handler to apply markers for all behaviors enabled
    for the given type.
    """

    markers = []
    for behavior in obj.__behaviors_schemas__:
        # only dynamic behaviors. Other behaviors are applied at
        # startup time to the base for_ interface
        if behavior.marker is not None:
            markers.append(behavior.marker)
    if len(markers) > 0:
        alsoProvides(obj, *markers)
