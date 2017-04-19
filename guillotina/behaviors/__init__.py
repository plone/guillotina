# so we can scan guillotina.behaviors and load behavior configuration
from . import dublincore  # noqa
from guillotina.interfaces import IBehaviorAssignable
from zope.interface import alsoProvides


def apply_markers(obj, event):
    """Event handler to apply markers for all behaviors enabled
    for the given type.
    """

    assignable = IBehaviorAssignable(obj, None)
    if assignable is None:
        return

    for behavior in assignable.enumerate_behaviors():
        if behavior.marker is not None:
            alsoProvides(obj, behavior.marker)
