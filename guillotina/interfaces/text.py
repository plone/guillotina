from guillotina import schema
from guillotina.i18n import MessageFactory
from guillotina.schema.interfaces import IObject
from zope.interface import Interface


_ = MessageFactory('guillotina')


class IRichText(IObject):
    """A text field that stores MIME type
    """

    default_mime_type = schema.ASCIILine(
        title=_(u"Default MIME type"),
        default='text/html',
    )

    output_mime_type = schema.ASCIILine(
        title=_(u"Default output MIME type"),
        default='text/x-html-safe'
    )

    allowed_mime_types = schema.Tuple(
        title=_(u"Allowed MIME types"),
        description=_(u"Set to None to disable checking"),
        default=None,
        required=False,
        value_type=schema.ASCIILine(title=u"MIME type"),
    )

    max_length = schema.Int(
        title=_(u'Maximum length'),
        description=_(u'in characters'),
        required=False,
        min=0,
        default=None,
    )


class IRichTextValue(Interface):
    """The value actually stored in a RichText field.
    This stores the following values on the parent object
      - A separate persistent object with the original value
      - A cache of the value transformed to the default output type
    The object is immutable.
    """

    raw = schema.Text(
        title=_(u"Raw value in the original MIME type"),
        readonly=True,
    )

    mimeType = schema.ASCIILine(
        title=_(u"MIME type"),
        readonly=True,
    )

    outputMimeType = schema.ASCIILine(
        title=_(u"Default output MIME type"),
        readonly=True,
    )

    encoding = schema.ASCIILine(
        title=_(u"Default encoding for the value"),
        description=_(u"Mainly used internally"),
        readonly=True,
    )

    raw_encoded = schema.ASCII(
        title=_(u"Get the raw value as an encoded string"),
        description=_(u"Mainly used internally"),
        readonly=True,
    )

    output = schema.Text(
        title=_(u"Transformed value in the target MIME type"),
        description=_(u"May be None if the transform cannot be completed"),
        readonly=True,
        required=False,
        missing_value=None,
    )
