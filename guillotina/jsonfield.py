# -*- encoding: utf-8 -*-
from guillotina.interfaces import IJSONField
from jsonschema import validate
from jsonschema import ValidationError
from zope.interface import implementer
from guillotina.schema._bootstrapfields import Field
from guillotina.schema.interfaces import WrongContainedType
from guillotina.schema.interfaces import WrongType

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
