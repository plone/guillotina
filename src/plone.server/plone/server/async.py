# -*- coding: utf-8 -*-
from zope.interface import Interface


class IAsyncUtility(Interface):

    async def initialize(self):
        pass
