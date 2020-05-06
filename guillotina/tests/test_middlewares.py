from guillotina.exceptions import PreconditionFailed
from guillotina.middlewares.errors import generate_error_response
from guillotina.response import HTTPInternalServerError
from guillotina.response import HTTPPreconditionFailed

import asyncio
import pytest
import time
import unittest


class AsgiMiddlewate:
    def __init__(self, app):
        self.next_app = app

    async def __call__(self, scope, receive, send):
        start = time.time()
        await asyncio.sleep(0.1)
        response = await self.next_app(scope, receive, send)
        end = time.time()

        response.headers["Measures"] = str(end - start)
        return response


@pytest.mark.asyncio
@pytest.mark.app_settings({"middlewares": ["guillotina.tests.test_middlewares.AsgiMiddlewate"]})
async def test_asgi_middleware(container_requester):
    async with container_requester as requester:
        response, _, headers = await requester.make_request("GET", "/")
        assert response == {
            "@type": "Application",
            "databases": ["db", "db-custom"],
            "static_directory": ["static", "module_static", "jsapp_static"],
            "static_file": ["favicon.ico"],
        }
        assert float(headers.get("measures")) > 0.1


def _makeOne(exc, request=None, error=None, bubble=False):
    return generate_error_response(exc, request, error, bubble)


class Test_generate_error_response(unittest.TestCase):
    def test_cancelled_error(self):
        resp = _makeOne(asyncio.CancelledError())
        assert resp.content["message"].startswith("Cancelled execution")
        self.assertEquals(resp.content["reason"], "unknownError")

    def test_other_error(self):
        resp = _makeOne(ValueError())
        assert resp.content["message"].startswith("Error on execution")
        self.assertEquals(resp.content["reason"], "unknownError")


@pytest.mark.asyncio
async def test_guillotina_exceptions_bubbling(container_requester):
    async with container_requester:
        exc = PreconditionFailed(None, None)

        # Don't bubble should return generic HTTPInternalServerError
        assert isinstance(_makeOne(exc, error="ViewError", bubble=False), HTTPInternalServerError)

        # Bubble should return the same
        assert isinstance(_makeOne(exc, error="ViewError", bubble=True), HTTPPreconditionFailed)

        # Generic exception with bubbling should still return HTTPInternalServerError
        assert isinstance(_makeOne(Exception, bubble=True), HTTPInternalServerError)

        # Check that error responses are bubbled directly too
        exc = HTTPPreconditionFailed()
        assert _makeOne(exc, error="ViewError", bubble=True) is exc
