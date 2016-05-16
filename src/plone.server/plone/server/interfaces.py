# -*- coding: utf-8 -*-
from zope.component.interfaces import ISite
from zope.interface import Interface


class IPloneSite(ISite):
    pass


class IRequest(Interface):
    pass


class IView(Interface):
    def __init__(context, request):
        pass

    async def __call__():
        pass
