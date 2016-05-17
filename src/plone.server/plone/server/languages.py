# -*- encoding: utf-8 -*-
from plone.server.api.layer import IDefaultLayer
from plone.server.interfaces import ILanguage

from zope.component import adapter
from zope.interface import implementer


class IEN(ILanguage):
    pass


class IENUS(IEN):
    pass


class ICA(ILanguage):
    pass


class IFI(ILanguage):
    pass


class DefaultLanguage(object):
    def translate(self):
        return self.context


@adapter(IDefaultLayer)
@implementer(IEN)
class EN(DefaultLanguage):
    def __init__(self, content):
        self.content = content


@adapter(IDefaultLayer)
@implementer(ICA)
class CA(DefaultLanguage):
    def __init__(self, content):
        self.content = content


@adapter(IDefaultLayer)
@implementer(IFI)
class FI(DefaultLanguage):
    def __init__(self, content):
        self.content = content


@adapter(IDefaultLayer)
@implementer(IENUS)
class ENUS(DefaultLanguage):
    def __init__(self, content):
        self.content = content
