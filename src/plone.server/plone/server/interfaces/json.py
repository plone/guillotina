from plone.server import _
from zope.interface import Interface, Attribute
from zope.interface import implementer
from zope.schema.interfaces import IField


class IJSONField(IField):
    """A text field that stores A JSON."""

    schema = Attribute(
        "schema",
        _("The JSON schema string serialization.")
    )


class IBeforeJSONAssignedEvent(Interface):
    """An object is going to be assigned to an attribute on another object.

    Subscribers to this event can change the object on this event to change
    what object is going to be assigned. This is useful, e.g. for wrapping
    or replacing objects before they get assigned to conform to application
    policy.
    """

    object = Attribute("The object that is going to be assigned.")

    name = Attribute("The name of the attribute under which the object "
                     "will be assigned.")

    context = Attribute("The context object where the object will be "
                        "assigned to.")
