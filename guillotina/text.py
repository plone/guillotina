# -*- encoding: utf-8 -*-
from guillotina import _
from guillotina.component import queryAdapter
from guillotina.db.orm.base import BaseObject
from guillotina.interfaces import IRichText
from guillotina.interfaces import IRichTextValue
from guillotina.interfaces import ITransformer
from guillotina.schema import Object
from guillotina.schema.exceptions import ConstraintNotSatisfied
from guillotina.schema.exceptions import WrongType
from guillotina.schema.interfaces import IFromUnicode
from zope.interface import implementer
from zope.interface import Invalid


class RawValueHolder(BaseObject):
    """Place the raw value in a separate persistent object.

    so that it does not get loaded when all we want is the output.
    """

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return u"<RawValueHolder: {0:s}>".format(self.value)

    def __eq__(self, other):
        if not isinstance(other, RawValueHolder):
            return NotImplemented
        return self.value == other.value

    def __ne__(self, other):
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal


@implementer(IRichTextValue)
class RichTextValue(object):
    """The actual value.

    Note that this is not a persistent object, to avoid a separate database object
    being loaded.
    """

    def __init__(self, raw=None, mimetype=None, outputmimetype=None,
                 encoding='utf-8', output=None):
        self._raw_holder = RawValueHolder(raw)
        self._mimeType = mimetype
        self._outputMimeType = outputmimetype
        self._encoding = encoding
    # the raw value - stored in a separate persistent object

    @property
    def raw(self):
        return self._raw_holder.value
    # Encoded raw value

    @property
    def encoding(self):
        return self._encoding

    @property
    def raw_encoded(self):
        if self._raw_holder.value is None:
            return ''
        happy_value = bytes(self._raw_holder.value,
                            encoding=self.encoding)
        return happy_value

    # the current mime type
    @property
    def mimeType(self):
        return self._mimeType
    # the default mime type

    @property
    def outputMimeType(self):
        return self._outputMimeType

    @property
    def output(self):
        return self.output_relative_to()

    def output_relative_to(self):
        """Transform the raw value to the output mimetype, within a specified context.

        If the value's mimetype is already the same as the output mimetype,
        no transformation is performed.

        The context parameter is relevant when the transformation is
        context-dependent. For example, Guillotina's resolveuid-and-caption
        transform converts relative links to absolute links using the context
        as a base.

        If a transformer cannot be found for the specified context, a
        transformer with the container as a context is used instead.
        """
        if self.mimeType == self.outputMimeType:
            return self.raw_encoded

        transformer = queryAdapter(self, ITransformer, self.outputMimeType)
        if transformer is None:
            return None

        return transformer()

    def __repr__(self):
        return u"RichTextValue object. (Did you mean <attribute>.raw or "\
               u"<attribute>.output?)"

    def __eq__(self, other):
        if not isinstance(other, RichTextValue):
            return NotImplemented
        return vars(self) == vars(other)

    def __ne__(self, other):
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal


@implementer(IRichText, IFromUnicode)
class RichText(Object):
    """Text field that also stores MIME type."""

    default_mime_type = 'text/html'
    output_mime_type = 'text/x-html-safe'
    allowed_mime_types = None
    max_length = None

    def __init__(self,
                 default_mime_type='text/html',
                 output_mime_type='text/x-html-safe',
                 allowed_mime_types=None,
                 max_length=None,
                 schema=IRichTextValue,
                 **kw
                 ):
        self.default_mime_type = default_mime_type
        self.output_mime_type = output_mime_type
        self.allowed_mime_types = allowed_mime_types
        self.max_length = max_length

        if 'default' in kw:
            default = kw['default']
            if isinstance(default, str):
                kw['default'] = self.from_string(default)
                kw['default'].readonly = True

        super(RichText, self).__init__(schema=schema, **kw)

    def from_string(self, str_val):
        return RichTextValue(
            raw=str_val,
            mimetype=self.default_mime_type,
            outputmimetype=self.output_mime_type,
            encoding='utf-8',
        )

    def _validate(self, value):
        if self.allowed_mime_types\
                and value.mimeType not in self.allowed_mime_types:
            raise WrongType(value, self.allowed_mime_types)

        if self.max_length is not None and len(value.raw) > self.max_length:
            raise Invalid(_(
                'msg_text_too_long',
                default=u'Text is too long. (Maximum ${max} characters.)',
                mapping={'max': self.max_length}
            ))

        if not self.constraint(value):
            raise ConstraintNotSatisfied(value)
