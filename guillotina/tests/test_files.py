from guillotina.exceptions import UnRetryableRequestError
from guillotina.files.utils import get_contenttype
from guillotina.files.utils import read_request_data
from guillotina.tests.utils import get_mocked_request

import pytest


async def test_read_request_data_handles_retries():
    request = get_mocked_request()
    request._retry_attempt = 1
    request._last_read_pos = 0
    request._cache_data = b"aaa"
    assert await read_request_data(request, 5) == b"aaa"


async def test_read_request_data_throws_exception_if_no_cache_data():
    request = get_mocked_request()
    request._retry_attempt = 1
    with pytest.raises(UnRetryableRequestError):
        await read_request_data(request, 5)


def test_get_content_type():
    class Foobar:
        content_type = "application/json"

    class Foobar2:
        filename = "foobar.json"

    assert get_contenttype(Foobar()) == "application/json"
    assert get_contenttype(Foobar2()) == "application/json"
    assert get_contenttype(None, default="application/json") == "application/json"
