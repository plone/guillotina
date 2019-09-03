from guillotina.tests.utils import make_mocked_request
from guillotina.utils import get_url

import json


def test_vhm_url(dummy_guillotina):
    request = make_mocked_request("GET", "/", {"X-VirtualHost-Monster": "https://foobar.com/foo/bar"})

    assert get_url(request, "/c/d") == "https://foobar.com/foo/bar/c/d"


def test_forwarded_proto_url(dummy_guillotina):
    request = make_mocked_request("GET", "/", {"X-Forwarded-Proto": "https"})
    url = get_url(request, "/c/d")
    assert url.startswith("https://")
    assert url.endswith("/c/d")


async def test_url_of_object_with_vhm(container_requester):
    async with container_requester as requester:
        resp, _ = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item"}),
            headers={"X-VirtualHost-Monster": "https://foobar.com/foo/bar"},
        )
        assert resp["@id"].startswith("https://foobar.com/foo/bar/db/guillotina")


async def test_url_of_object_with_scheme(container_requester):
    async with container_requester as requester:
        resp, _ = await requester(
            "POST",
            "/db/guillotina/",
            data=json.dumps({"@type": "Item", "id": "foobar"}),
            headers={"X-VirtualHost-Monster": "https://foobar.com/foo/bar"},
        )
        url = resp["@id"]
        assert url.startswith("https://")
        assert url.endswith("/db/guillotina/foobar")


def test_vh_path_url(dummy_guillotina):
    request = make_mocked_request("GET", "/", {"X-VirtualHost-Path": "/foo/bar"})

    assert get_url(request, "/c/d").endswith("/foo/bar/c/d")
