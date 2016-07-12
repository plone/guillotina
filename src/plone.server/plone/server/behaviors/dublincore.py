# -*- encoding: utf-8 -*-
from plone.dexterity.interfaces import IFormFieldProvider
from plone.supermodel import model
from zope import schema
from zope.interface import provider
from plone.dexterity.interfaces import IDexterityContent
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter


@provider(IFormFieldProvider)
class IDublinCore(model.Schema):
    """We basically just want the IFormFieldProvider interface applied
        There's probably a zcml way of doing this. """
    created = schema.Datetime(
        title=u'Creation Date',
        description=u"The date and time that an object is created. "
        u"\nThis is normally set automatically."
        )

    modified = schema.Datetime(
        title=u'Modification Date',
        description=u"The date and time that the object was last modified in a\n"
        u"meaningful way."
        )


@adapter(IDexterityContent)
class DublinCore(ZDCAnnotatableAdapter):
    pass
