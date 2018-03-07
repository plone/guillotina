from aiohttp.web_exceptions import HTTPPreconditionFailed
from guillotina import configure
from guillotina.interfaces import IErrorResponseException

import json


@configure.adapter(
    for_=json.decoder.JSONDecodeError,
    provides=IErrorResponseException)
def json_decode_error_response(exc, error='', eid=None):
    return HTTPPreconditionFailed(
        reason=f'JSONDecodeError: {eid}')
