from guillotina.tests.utils import make_mocked_request
from multidict import CIMultiDict

import asyncio


async def test_execute_futures():
    req = make_mocked_request("GET", "/")
    req.add_future("sleep", asyncio.sleep(0.01))
    assert req.get_future("sleep") is not None
    assert req.get_future("sleep2") is None
    task = req.execute_futures()
    await asyncio.wait_for(task, 1)
    assert task.done()


async def test_get_uid():
    req = make_mocked_request("GET", "/")
    assert req.uid is not None


async def test_get_uid_from_forwarded():
    req = make_mocked_request("GET", "/", headers={"X-FORWARDED-REQUEST-UID": "foobar"})
    assert req.uid == "foobar"


async def test_get_content_type():
    raw_headers = [("Content-Type", "application/json")]
    headers = CIMultiDict(raw_headers)
    req = make_mocked_request("GET", "/", headers=headers)
    assert req.content_type == "application/json"


async def test_get_headers():
    raw_headers = [("a", "1"), ("a", "2"), ("b", "3")]
    headers = CIMultiDict(raw_headers)
    req = make_mocked_request("GET", "/", headers=headers)
    assert req.headers == headers

    for k, v in raw_headers:
        assert (bytes(k, "utf-8"), bytes(v, "utf-8")) in req.raw_headers


async def test_get_query():
    req = make_mocked_request("GET", "/", query_string=b"q=blabla")
    assert req.query.get("q") == "blabla"

    req = make_mocked_request("GET", "/", query_string=b"flag")
    assert "flag" in req.query


async def test_get_path():
    req = make_mocked_request("GET", "/some/path", query_string=b"q=blabla")
    assert req.path == "/some/path"


async def test_get_content():
    req = make_mocked_request("GET", "/", payload=b"X" * 2048)
    body = bytes(await req.content.read())
    assert body == b"X" * 2048


async def test_body_exist():
    req = make_mocked_request("GET", "/", payload=b"X" * 2048)
    assert await req.body_exists is True


async def test_not_body_exist():
    req = make_mocked_request("GET", "/")
    assert await req.body_exists is False


async def test_get_forward_proto(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina", headers={"X-Forwarded-Proto": "https"})
        assert response["@id"].startswith("https")
