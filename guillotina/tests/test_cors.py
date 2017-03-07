# -*- coding: utf-8 -*-


async def test_get_root(site_requester):
    async for requester in site_requester:
        response = await requester.make_request(
            'OPTIONS', '/guillotina/guillotina', headers={
                'Origin': 'http://localhost',
                'Access-Control-Request-Method': 'Get'
            })
        assert 'ACCESS-CONTROL-ALLOW-CREDENTIALS' in response.headers
        assert 'ACCESS-CONTROL-EXPOSE-HEADERS' in response.headers
        assert 'ACCESS-CONTROL-ALLOW-HEADERS' in response.headers
