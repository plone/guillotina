from openapi_spec_validator import validate_v3_spec

import json
import os
import pytest


pytestmark = pytest.mark.asyncio


SWAGGER_SETTINGS = {"applications": ["guillotina.contrib.swagger"]}


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_get_swagger_definition(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/@swagger")
        assert status == 200
        assert "/" in resp["paths"]

    async with container_requester as requester:
        resp, status = await requester("GET", "/db/@swagger")
        assert status == 200
        assert "/db" in resp["paths"]

    async with container_requester as requester:
        resp, status = await requester("GET", "/db/guillotina/@swagger")
        assert status == 200
        assert "/db/guillotina" in resp["paths"]


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_get_swagger_index(container_requester):
    async with container_requester as requester:
        resp, status = await requester("GET", "/@docs")
        assert status == 200


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_validate_swagger_definition(container_requester):
    async with container_requester as requester:
        for path in ("/", "/db", "/db/guillotina"):
            resp, status = await requester("GET", os.path.join(path, "@swagger"))
            assert status == 200
            validate_v3_spec(resp)


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_validate_arrays_in_query_params(container_requester):
    async with container_requester as requester:
        _, status = await requester("GET", "@queryParamsValidation?numbers=1.0&numbers=2")
        assert status == 200

        _, status = await requester("GET", "@queryParamsValidation?users=u1&users=u2&users=u3")
        assert status == 200

        resp, status = await requester("GET", "@queryParamsValidation?users=u1&users=")
        assert status == 412
        assert resp["validator"] == "minLength"

        resp, status = await requester("GET", "@queryParamsValidation?users=u1")
        assert status == 412
        assert resp["validator"] == "minItems"

        resp, status = await requester(
            "GET", "@queryParamsValidation?users=u1&users=u2&users=u3&users=u4&users=u5&users=u6"
        )
        assert status == 412
        assert resp["validator"] == "maxItems"


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_validate_numbers_and_integers_in_query_params(container_requester):
    async with container_requester as requester:
        _, status = await requester("GET", "@queryParamsValidation?oranges=5")
        assert status == 200

        _, status = await requester("GET", "@queryParamsValidation?kilograms=60.3")
        assert status == 200

        resp, status = await requester("GET", "@queryParamsValidation?oranges=0")
        assert status == 412
        assert resp["validator"] == "minimum"

        resp, status = await requester("GET", "@queryParamsValidation?kilograms=3.2")
        assert status == 412
        assert resp["validator"] == "minimum"


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_can_have_optional_request_body(container_requester):
    async with container_requester as requester:
        # Check that if there is body in the request, it is validated
        # against schema
        for invalid_body in ({"foo": "bar"}, {}):
            resp, status = await requester("POST", "@optionalRequestBody", data=json.dumps(invalid_body))
            assert resp["reason"] == "json schema validation error"
            assert status == 412

        _, status = await requester("POST", "@optionalRequestBody", data=json.dumps({"valid": "body"}))
        assert status == 200

        # Check that since it's optional, we can just not send it
        _, status = await requester("POST", "@optionalRequestBody")
        assert status == 200
