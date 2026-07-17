from guillotina.exceptions import DeserializationError
from guillotina.exceptions import ValueDeserializationError
from unittest import mock

import asyncio


async def test_non_existing_container(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/non")
        assert status == 404


async def test_non_existing_registry(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@registry/non")
        assert status == 404


async def test_non_existing_type(container_requester):
    async with container_requester as requester:
        response, status = await requester("GET", "/db/guillotina/@types/non")
        assert status == 404


def test_deserialization_error_formats_error():
    error = DeserializationError([{"error": "Foobar", "field": "foobar_field"}])
    assert "foobar_field" in str(error)


def test_value_serialization_error():
    error = ValueDeserializationError("Foo", "Bar", "Something wrong")
    assert error.field == "Foo"
    assert error.value == "Bar"


async def test_handle_cancelled_error(container_requester):
    async with container_requester as requester:
        with mock.patch("guillotina.traversal.TraversalRouter.real_resolve") as handle_mock:  # noqa
            f = asyncio.Future()
            f.set_result(None)
            handle_mock.return_value = f
            handle_mock.side_effect = asyncio.CancelledError()
            response, status = await requester("GET", "/db")
            assert status == 499


async def test_unhandle_exception_in_view(container_requester):
    async with container_requester as requester:
        with mock.patch("guillotina.traversal.TraversalRouter.real_resolve") as handle_mock:  # noqa
            f = asyncio.Future()
            f.set_result(None)
            handle_mock.return_value = f
            handle_mock.side_effect = Exception()
            _, status = await requester("GET", "/db")
            assert status == 500


async def test_error_response_is_json_even_when_html_accepted(container_requester):
    async with container_requester as requester:
        response, status, headers = await requester.make_request("GET", "/db/non", accept="text/html,*/*")
        assert status == 404
        assert "application/json" in headers["Content-Type"]
        assert "text/html" not in headers["Content-Type"]
        assert b"<html" not in (response if isinstance(response, bytes) else b"")


async def test_error_response_does_not_reflect_markup_as_html(container_requester):
    async with container_requester as requester:
        payload = "<img src=x onerror=alert(document.domain)>"
        data = '{{"@type": "{}"}}'.format(payload)
        _, status, headers = await requester.make_request(
            "POST", "/db/guillotina", data=data, accept="text/html,*/*"
        )
        assert status >= 400
        assert "application/json" in headers["Content-Type"]
        assert "text/html" not in headers["Content-Type"]
