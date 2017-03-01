from guillotina import configure
from guillotina.interfaces import IRichTextValue
from guillotina.interfaces import ITransformer


# @configure.adapter(
#     for_=IRichTextValue,
#     provides=ITransformer,
#     name='text/x-uppercase')
class Upper(object):

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return self.context.raw_encoded.upper()
