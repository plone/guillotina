# -*- coding: utf-8 -*-
from guillotina.interfaces.exceptions import ISerializableException
from zope.interface import implementer

import json


@implementer(ISerializableException)
class DeserializationError(Exception):
    """An error happened during deserialization of content.
    """

    def __init__(self, errors):
        self.msg = 'Error deserializing content'
        self.errors = errors

    def __str__(self):
        return '{} ({})'.format(
            self.msg,
            json.dumps(self.json_data()))

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


class QueryParsingError(Exception):
    """An error happened while parsing a search query.
    """
