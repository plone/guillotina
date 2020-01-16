from openapi_spec_validator import validate_v3_spec

import os
import pytest


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
