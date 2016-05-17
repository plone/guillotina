from plone.registry import field
from zope.interface import Interface


class ILayers(Interface):

    active_layers = field.List(
        title=u"Active Layers",
        default=[],
        value_type=field.TextLine(title=u"Value"))
