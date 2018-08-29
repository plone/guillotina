from copy import deepcopy

import pytest

from aiohttp.web_exceptions import HTTPUnauthorized
from guillotina import cors
from guillotina._settings import app_settings
from guillotina.tests.utils import get_mocked_request


async def test_get_root(container_requester):
    async with container_requester as requester:
        value, status, headers = await requester.make_request(
            'OPTIONS', '/db/guillotina', headers={
                'Origin': 'http://localhost',
                'Access-Control-Request-Method': 'Get'
            })
        assert 'ACCESS-CONTROL-ALLOW-CREDENTIALS' in headers
        assert 'ACCESS-CONTROL-EXPOSE-HEADERS' in headers
        assert 'ACCESS-CONTROL-ALLOW-HEADERS' in headers


async def test_get_endpoint(container_requester):
    async with container_requester as requester:
        value, status, headers = await requester.make_request(
            'OPTIONS', '/db/guillotina/@types', headers={
                'Origin': 'http://localhost',
                'Access-Control-Request-Method': 'Get'
            })
        assert 'ACCESS-CONTROL-ALLOW-CREDENTIALS' in headers
        assert 'ACCESS-CONTROL-EXPOSE-HEADERS' in headers
        assert 'ACCESS-CONTROL-ALLOW-HEADERS' in headers


class _CorsTestRenderer(cors.DefaultCorsRenderer):

    def __init__(self, request, settings):
        self.request = request
        self.settings = settings

    async def get_settings(self):
        settings = deepcopy(app_settings['cors'])
        settings.update(self.settings)
        return settings


async def test_allow_origin_star():
    request = get_mocked_request(headers={
        'Origin': 'http://localhost:8080'
    })
    renderer = _CorsTestRenderer(request, {
        'allow_origin': ['*']
    })
    headers = await renderer.get_headers()
    assert headers['Access-Control-Allow-Origin'] == '*'


async def test_bad_origin():
    request = get_mocked_request(headers={
        'Origin': 'http://foobar.com:8080'
    })
    renderer = _CorsTestRenderer(request, {
        'allow_origin': ['localhost']
    })
    with pytest.raises(HTTPUnauthorized):
        await renderer.get_headers()


async def test_allow_origin_foobar():
    request = get_mocked_request(headers={
        'Origin': 'http://foobar.com:8080'
    })
    renderer = _CorsTestRenderer(request, {
        'allow_origin': ['http://foobar.com:8080']
    })
    headers = await renderer.get_headers()
    assert headers['Access-Control-Allow-Origin'] == 'http://foobar.com:8080'
