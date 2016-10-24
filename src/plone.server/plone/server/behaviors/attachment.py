from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.interfaces import IFormFieldProvider
from plone.dexterity.utils import safe_str
from plone.i18n.locales.languages import _languagelist
from plone.server import _
from plone.server import DICT_LANGUAGES
from plone.supermodel import model
from plone.supermodel.directives import catalog
from plone.supermodel.directives import index
from plone.uuid.interfaces import IUUID
from zope import schema
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary
from plone.server.file import BasicFileField
from plone.server.behaviors.properties import ContextProperty


@provider(IFormFieldProvider)
class IAttachment(model.Schema):
    file = BasicFileField(
        title=u'File',
        required=False
    )


@adapter(IDexterityContent)
class Attachment(ZDCAnnotatableAdapter):

    file = ContextProperty(u'file', None)

    def __init__(self, context):
        self.context = context
        super(Attachment, self).__init__(context)
