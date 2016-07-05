# -*- coding: utf-8 -*-
from zope.component.interfaces import ISite
from zope.interface import Interface
from plone.supermodel import model
from zope import schema

DEFAULT_READ_PERMISSION = 'plone.ViewContent'
DEFAULT_WRITE_PERMISSION = 'plone.ManageContent'


class IApplication(Interface):
    pass


class IDataBase(Interface):
    pass


class IStaticFile(Interface):
    pass


class IStaticDirectory(Interface):
    pass


class IPloneSite(model.Schema, ISite):
    title = schema.TextLine(
        title='Title',
        required=False,
        description=u"Title of the Site",
        default=u''
    )


class IContentNegotiation(Interface):
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


class ITraversableView(IView):

    def publishTraverse(traverse_to):
        pass


class IDownloadView(IView):
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
