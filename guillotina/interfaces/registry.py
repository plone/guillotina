from guillotina import schema
from guillotina.i18n import MessageFactory
from zope.interface import Interface


_ = MessageFactory("guillotina")


class ILayers(Interface):

    active_layers = schema.FrozenSet(
        title=_("Active Layers"), defaultFactory=frozenset, value_type=schema.TextLine(title="Value")
    )


class IAddons(Interface):

    enabled = schema.FrozenSet(
        title=_("Installed addons"),
        defaultFactory=frozenset,
        value_type=schema.TextLine(title="Value"),
        description=_("""List of enabled addons"""),
    )
