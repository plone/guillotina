from zope.component import adapter
from zope.interface import implementer
from plone.server.interfaces import IRichTextValue
from plone.server.interfaces import ITransformer


@adapter(IRichTextValue)
@implementer(ITransformer)
class Upper(object):

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return self.context.raw_encoded.upper()
