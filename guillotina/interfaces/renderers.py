from zope.interface import Interface


# Classes as for marker objects to lookup
class IRenderFormats(Interface):
    pass


# Marker objects/interfaces to look for
class IRendererFormatHtml(IRenderFormats):
    pass


class IRendererFormatPlain(IRenderFormats):
    pass


class IRendererFormatJson(IRenderFormats):
    pass


class IRendererFormatRaw(IRenderFormats):
    pass
