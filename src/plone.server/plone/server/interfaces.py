# -*- coding: utf-8 -*-
from zope.component.interfaces import ISite
from zope.interface import Interface


class IPloneSite(ISite):
    pass


class IRequest(Interface):
    pass


class IResponse(Interface):

    def __init__(context, request):
        pass


class IView(Interface):

    def __init__(context, request):
        pass

    async def __call__(self):
        pass


class IGET(IView):
    pass


class IPUT(IView):
    pass


class IPOST(IView):
    pass


class IPATCH(IView):
    pass


class IDELETE(IView):
    pass


class IOPTIONS(IView):
    pass

# Classes as for marker objects to lookup


class IRenderFormats(Interface):
    pass


class ILanguage(Interface):
    pass


# Target interfaces on resolving

class IRendered(Interface):
    pass


class ITranslated(Interface):
    pass
