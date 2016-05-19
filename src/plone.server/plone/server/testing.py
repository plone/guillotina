# -*- coding: utf-8 -*-
from zope.component import testlayer

import plone.server
import zope.component


ZCMLLayer = testlayer.ZCMLFileLayer(plone.server, 'configure.zcml')


class ZopeComponentLayer(testlayer.LayerBase):
    pass


class PloneLayer(object):
    __name__ = 'Layer'
    __bases__ = (
        ZopeComponentLayer(zope.component),
        ZCMLLayer
    )


PLONE_LAYER = PloneLayer()
