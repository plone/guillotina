# -*- encoding: utf-8 -*-
from guillotina.component import adapter
from guillotina.component import provideAdapter
from guillotina.db.orm.base import BaseObject
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import ITransformer
from guillotina.interfaces import TransformError
from guillotina.schema.exceptions import ConstraintNotSatisfied
from guillotina.schema.exceptions import WrongType
from guillotina.schema.interfaces import IFromUnicode
from guillotina.text import RichText
from guillotina.text import RichTextValue
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.exceptions import Invalid

import pytest


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


def test_field():
    field = IContent['rich']
    assert field.default_mime_type == 'text/html'
    assert field.output_mime_type == 'text/x-html-safe'
    assert field.allowed_mime_types is None
    assert field.max_length is None


def test_value():
    field = IContent2['rich']
    value = RichTextValue(
        raw=u"Some plain text",
        mimetype='text/plain',
        outputmimetype=field.output_mime_type,
        encoding='utf-8')
    assert value.output is None
    provideAdapter(Transformer, name='text/x-uppercase')
    assert value.output == 'SOME PLAIN TEXT'
    assert value.encoding == 'utf-8'
    assert value.raw_encoded == b'Some plain text'
    value2 = RichTextValue(
        raw=u"Some plain text",
        mimetype='text/plain',
        outputmimetype=field.output_mime_type,
        encoding='utf-8')
    assert value == value2
    assert value is not None


def test_unicode():
    field = IContent2['rich']
    assert IFromUnicode.providedBy(field)
    value = field.from_string("A plain text string")
    assert value.mimeType == 'text/plain'
    assert value.outputMimeType == 'text/x-uppercase'
    assert value.raw == 'A plain text string'
    assert value.raw_encoded == b'A plain text string'


def test_validation():
    field = IContent2['rich']
    value = field.from_string("A plain text string")
    field.allowed_mime_types = None
    field.validate(value)
    field.allowed_mime_types = ('text/html',)
    with pytest.raises(WrongType):
        field.validate(value)
    field.allowed_mime_types = ('text/plain', 'text/html',)
    field.validate(value)
    long_value = field.from_string('x' * (field.max_length + 1))
    with pytest.raises(Invalid):
        field.validate(long_value)
    field.constraint = lambda value: False
    with pytest.raises(ConstraintNotSatisfied):
        field.validate(value)


def test_default_value():
    default_field = RichText(
        __name__='default_field',
        title=u"Rich text",
        default_mime_type='text/plain',
        output_mime_type='text/x-uppercase',
        allowed_mime_types=('text/plain', 'text/html',),
        default=u"Default value")
    assert default_field.default.__class__ == RichTextValue
    assert default_field.default.raw == u'Default value'
    assert default_field.default.outputMimeType == 'text/x-uppercase'
    assert default_field.default.mimeType == 'text/plain'


def test_persistence():
    field = IContent2['rich']
    value = field.from_string("A plain text string")
    assert not IBaseObject.providedBy(value)
    assert IBaseObject.providedBy(value._raw_holder)
