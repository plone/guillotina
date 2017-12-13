# so we can scan guillotina.behaviors and load behavior configuration
from . import attachment  # noqa
from . import dublincore  # noqa
from guillotina._cache import BEHAVIOR_CACHE
from guillotina._cache import SCHEMA_CACHE
from guillotina.interface import also_provides
from guillotina.profile import profilable


def enumerate_behaviors(ob):
    for behavior in SCHEMA_CACHE[ob.type_name]['behaviors']:
        yield behavior
    for behavior in ob.__behaviors__:
        yield BEHAVIOR_CACHE[behavior]


@profilable
def apply_markers(obj, event=None):
    """Event handler to apply markers for all behaviors enabled
    for the given type.
    """

    markers = []
    for behavior in enumerate_behaviors(obj):
        if behavior.marker is not None:
            markers.append(behavior.marker)
    also_provides(obj, *markers)
