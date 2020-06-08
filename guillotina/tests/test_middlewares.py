from guillotina.middlewares.errors import generate_error_response

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


class Test_generate_error_response(unittest.TestCase):
    def _makeOne(self, exc, request=None):
        return generate_error_response(exc, request)

    def test_cancelled_error(self):
        resp = self._makeOne(asyncio.CancelledError())
        assert resp.content["message"].startswith("Cancelled execution")
        self.assertEquals(resp.content["reason"], "unknownError")

    def test_other_error(self):
        resp = self._makeOne(ValueError())
        assert resp.content["message"].startswith("Error on execution")
        self.assertEquals(resp.content["reason"], "unknownError")
