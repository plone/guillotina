from plone.server import configure
from plone.server.interfaces import IRichTextValue
from plone.server.interfaces import ITransformer


# @configure.adapter(
#     for_=IRichTextValue,
#     provides=ITransformer,
#     name='text/x-uppercase')
class Upper(object):

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return self.context.raw_encoded.upper()
