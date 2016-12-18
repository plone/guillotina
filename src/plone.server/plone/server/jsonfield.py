# -*- encoding: utf-8 -*-
from zope.schema._bootstrapfields import Field
from jsonschema import validate, ValidationError
from zope.schema.interfaces import WrongType
from zope.schema.interfaces import WrongContainedType
from zope.event import notify
from zope.interface import implementer
from plone.server.interfaces import IJSONField

import json


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
