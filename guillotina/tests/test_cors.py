# -*- coding: utf-8 -*-


async def test_get_root(container_requester):
    async with await container_requester as requester:
        value, status, headers = await requester.make_request(
            'OPTIONS', '/db/guillotina', headers={
                'Origin': 'http://localhost',
                'Access-Control-Request-Method': 'Get'
            })
        assert 'ACCESS-CONTROL-ALLOW-CREDENTIALS' in headers
        assert 'ACCESS-CONTROL-EXPOSE-HEADERS' in headers
        assert 'ACCESS-CONTROL-ALLOW-HEADERS' in headers
