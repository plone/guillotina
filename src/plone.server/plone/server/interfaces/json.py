from plone.server import _
from zope.interface import Interface, Attribute
from zope.interface import implementer
from zope.schema.interfaces import IField
from zope.schema._bootstrapfields import Field
from jsonschema import validate, ValidationError
from zope.schema.interfaces import WrongType
from zope.schema.interfaces import WrongContainedType
from zope.event import notify

import json


class IJSONField(IField):
    """A text field that stores A JSON."""

    schema = Attribute(
        "schema",
        _("The JSON schema string serialization.")
    )


@implementer(IJSONField)
class JSONField(Field):

    def __init__(self, schema, **kw):
        if not isinstance(schema, str):
            raise WrongType

        try:
            self.schema = json.loads(schema)
        except ValueError:
            raise WrongType
        super(JSONField, self).__init__(**kw)

    def _validate(self, value):
        super(JSONField, self)._validate(value)

        try:
            validate(value, self.schema)
        except ValidationError as e:
            raise WrongContainedType(e.message, self.__name__)

    def set(self, object, value):
        # Announce that we're going to assign the value to the object.
        # Motivation: Widgets typically like to take care of policy-specific
        # actions, like establishing location.
        event = BeforeJSONAssignedEvent(value, self.__name__, object)
        notify(event)
        # The event subscribers are allowed to replace the object, thus we need
        # to replace our previous value.
        value = event.object
        super(JSONField, self).set(object, value)


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


@implementer(IBeforeJSONAssignedEvent)
class BeforeJSONAssignedEvent(object):
    """An object is going to be assigned to an attribute on another object."""

    def __init__(self, object, name, context):
        self.object = object
        self.name = name
        self.context = context
