from aiohttp.web_exceptions import HTTPConflict
from aiohttp.web_exceptions import HTTPPreconditionFailed
from guillotina import configure
from guillotina import error_reasons
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import DeserializationError
from guillotina.exceptions import NotAllowedContentType
from guillotina.exceptions import PreconditionFailed
from guillotina.interfaces import IErrorResponseException

import json


def render_error_response(error, reason, eid=None):
    data = {
        'reason': reason.name,
        'details': reason.details,
        'type': error
    }
    if eid is not None:
        data['eid'] = eid
    return data


def exception_handler_factory(reason, name='PreconditionFailed',
                              klass=HTTPPreconditionFailed,
                              serialize_exc=False):
    def handler(exc, error='', eid=None):
        data = render_error_response(name, reason, eid)
        if serialize_exc:
            data['message'] = str(exc)
        return klass(
            text=json.dumps(data),
            headers={
                'Content-Type': 'application/json'
            })
    return handler


def register_handler_factory(ExceptionKlass, factory):
    configure.adapter(
        for_=ExceptionKlass,
        provides=IErrorResponseException)(factory)


register_handler_factory(
    json.decoder.JSONDecodeError,
    exception_handler_factory(error_reasons.JSON_DECODE))
register_handler_factory(
    PreconditionFailed,
    exception_handler_factory(error_reasons.PRECONDITION_FAILED,
                              serialize_exc=True))
register_handler_factory(
    NotAllowedContentType,
    exception_handler_factory(error_reasons.NOT_ALLOWED,
                              serialize_exc=True))
register_handler_factory(
    ConflictIdOnContainer,
    exception_handler_factory(error_reasons.CONFLICT_ID, 'ConflictId',
                              serialize_exc=True, klass=HTTPConflict))
register_handler_factory(
    DeserializationError,
    exception_handler_factory(error_reasons.DESERIALIZATION_FAILED,
                              'DeserializationError',
                              serialize_exc=True))
