from aiohttp.web import Response
from guillotina.tests.utils import get_mocked_request
from guillotina.traversal import _apply_cors

import pytest


class CorsTestRenderer:
    def __init__(self, settings):
        pass

    async def get_headers(self):
        return {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "*",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3660",
        }


@pytest.mark.app_settings({"cors_renderer": "guillotina.tests.test_traversal.CorsTestRenderer"})
async def test_apply_cors(guillotina_main):
    request = get_mocked_request()
    resp = Response(
        headers={
            "Access-Control-Allow-Origin": "http://localhost:8080",
            "Access-Control-Allow-Methods": "GET, PUT, PATCH",
            "Access-Control-Expose-Headers": "Location",
            "Location": "/test",
        }
    )
    resp = await _apply_cors(request, resp)
    assert resp.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    assert resp.headers["Access-Control-Allow-Methods"] == "GET, POST, PUT, PATCH"
    assert resp.headers["Access-Control-Allow-Headers"] == "*"
    assert resp.headers["Access-Control-Expose-Headers"] == "*"
    assert resp.headers["Access-Control-Allow-Credentials"] == "true"
    assert resp.headers["Access-Control-Max-Age"] == "3660"
    assert resp.headers["Location"] == "/test"
