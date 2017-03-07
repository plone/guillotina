# -*- encoding: utf-8 -*-
from guillotina.db.orm.base import BaseObject
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import ITransformer
from guillotina.interfaces import TransformError
from guillotina.testing import GuillotinaFunctionalTestCase
from guillotina.text import RichText
from guillotina.text import RichTextValue
from zope.component import adapter
from zope.component import provideAdapter
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.exceptions import Invalid
from guillotina.schema.exceptions import ConstraintNotSatisfied
from guillotina.schema.exceptions import WrongType
from guillotina.schema.interfaces import IFromUnicode


class IContent(Interface):
    rich = RichText(title=u"Rich Text")


class IContent2(Interface):
    rich = RichText(title=u"Rich text",
                    default_mime_type='text/plain',
                    output_mime_type='text/x-uppercase',
                    allowed_mime_types=('text/plain', 'text/html',),
                    max_length=500)


@implementer(IContent2)
class Content(BaseObject):

    def __init__(self, rich=None):
        self.rich = rich


@adapter(Interface)
@implementer(ITransformer)
class Transformer(object):

    def __init__(self, context):
        self.context = context

    def __call__(self):
        if not self.context.mimeType.startswith('text/'):
            raise TransformError("Can only work with text")
        return self.context.raw.upper()


class FunctionalTestServer(GuillotinaFunctionalTestCase):
    """Functional testing of the API REST."""

    def test_field(self):
        field = IContent['rich']
        self.assertEqual(field.default_mime_type, 'text/html')
        self.assertEqual(field.output_mime_type, 'text/x-html-safe')
        self.assertEqual(field.allowed_mime_types, None)
        self.assertEqual(field.max_length, None)

    def test_value(self):
        field = IContent2['rich']
        value = RichTextValue(
            raw=u"Some plain text",
            mimetype='text/plain',
            outputmimetype=field.output_mime_type,
            encoding='utf-8')
        self.assertEqual(value.output, None)
        provideAdapter(Transformer, name='text/x-uppercase')
        self.assertEqual(value.output, 'SOME PLAIN TEXT')
        self.assertEqual(value.encoding, 'utf-8')
        self.assertEqual(value.raw_encoded, b'Some plain text')
        value2 = RichTextValue(
            raw=u"Some plain text",
            mimetype='text/plain',
            outputmimetype=field.output_mime_type,
            encoding='utf-8')
        self.assertTrue(value == value2)
        self.assertFalse(value != value2)
        self.assertFalse(value is None)
        self.assertTrue(value is not None)

    def test_unicode(self):
        field = IContent2['rich']
        self.assertTrue(IFromUnicode.providedBy(field))
        value = field.from_string("A plain text string")
        self.assertEqual(value.mimeType, 'text/plain')
        self.assertEqual(value.outputMimeType, 'text/x-uppercase')
        self.assertEqual(value.raw, 'A plain text string')
        self.assertEqual(value.raw_encoded, b'A plain text string')

    def test_validation(self):
        field = IContent2['rich']
        value = field.from_string("A plain text string")
        field.allowed_mime_types = None
        field.validate(value)
        field.allowed_mime_types = ('text/html',)
        self.assertRaises(WrongType, field.validate, value)
        field.allowed_mime_types = ('text/plain', 'text/html',)
        field.validate(value)
        long_value = field.from_string('x' * (field.max_length + 1))
        self.assertRaises(Invalid, field.validate, long_value)
        field.constraint = lambda value: False
        self.assertRaises(ConstraintNotSatisfied, field.validate, value)

    def test_default_value(self):
        default_field = RichText(
            __name__='default_field',
            title=u"Rich text",
            default_mime_type='text/plain',
            output_mime_type='text/x-uppercase',
            allowed_mime_types=('text/plain', 'text/html',),
            default=u"Default value")
        self.assertEqual(default_field.default.__class__, RichTextValue)
        self.assertEqual(default_field.default.raw, u'Default value')
        self.assertEqual(
            default_field.default.outputMimeType, 'text/x-uppercase')
        self.assertEqual(default_field.default.mimeType, 'text/plain')

    def test_persistence(self):
        field = IContent2['rich']
        value = field.from_string("A plain text string")
        self.assertFalse(IBaseObject.providedBy(value))
        self.assertTrue(IBaseObject.providedBy(value._raw_holder))
