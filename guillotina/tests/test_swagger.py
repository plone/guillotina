import pytest


SWAGGER_SETTINGS = {
    "applications": ["guillotina.contrib.swagger"]
}


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_get_swagger_definition(container_requester):
    async with container_requester as requester:
        resp, status = await requester('GET', '/@swagger')
        assert status == 200
        assert '/' in resp['paths']

    async with container_requester as requester:
        resp, status = await requester('GET', '/db/@swagger')
        assert status == 200
        assert '/db' in resp['paths']

    async with container_requester as requester:
        resp, status = await requester('GET', '/db/guillotina/@swagger')
        assert status == 200
        assert '/db/guillotina' in resp['paths']


@pytest.mark.app_settings(SWAGGER_SETTINGS)
async def test_get_swagger_index(container_requester):
    async with container_requester as requester:
        resp, status = await requester('GET', '/@docs')
        assert status == 200
