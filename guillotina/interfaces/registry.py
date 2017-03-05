# -*- encoding: utf-8 -*-
from zope.interface import Interface
from zope import schema
from zope.i18nmessageid import MessageFactory
from collections import UserDict

_ = MessageFactory('guillotina')


class ILayers(Interface):

    active_layers = schema.FrozenSet(
        title=_('Active Layers'),
        defaultFactory=UserDict,
        value_type=schema.TextLine(
            title='Value'
        )
    )


class IAddons(Interface):

    enabled = schema.FrozenSet(
        title=_('Installed addons'),
        defaultFactory=UserDict,
        value_type=schema.TextLine(
            title='Value'
        ),
        description=_("""List of enabled addons""")
    )
