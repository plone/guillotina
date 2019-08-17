from guillotina.tests.utils import make_mocked_request

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


async def test_get_forward_proto(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina", headers={"X-Forwarded-Proto": "https"})
        assert response["@id"].startswith("https")
