import asyncio
import pytest
import time


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
