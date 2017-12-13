# -*- coding: utf-8 -*-
from guillotina.interface import implementer
from guillotina.interfaces.exceptions import ISerializableException

import ujson


@implementer(ISerializableException)
class DeserializationError(Exception):
    """An error happened during deserialization of content.
    """

    def __init__(self, errors):
        self.msg = self.message = 'Error deserializing content'
        self.errors = errors

    def __str__(self):
        return '{} ({})'.format(
            self.msg,
            ujson.dumps(self.json_data()))

    def json_data(self):
        errors = []
        for error in self.errors:
            # need to clean raw exceptions out of this list here...
            error = error.copy()
            if 'error' in error:
                error.pop('error')
            errors.append(error)
        return {
            'deserialization_errors': errors
        }


class ValueDeserializationError(Exception):
    """An error happened during deserialization of content.
    """

    def __init__(self, field, value, msg):
        self.msg = self.message = 'Error deserializing content'
        self.field = field
        self.value = value


class QueryParsingError(Exception):
    """An error happened while parsing a search query.
    """
