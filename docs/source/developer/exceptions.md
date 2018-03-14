# Exceptions

Exceptions during the rendering of API calls are wrapped, logged and provided
generic http status codes by default.

Guillotina provides a mechanism for customizing the status codes and type of
responses given depending on the exception type.

## Custom exception response

```python
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
```
