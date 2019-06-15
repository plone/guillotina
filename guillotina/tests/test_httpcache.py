import json


async def test_returned_on_default_get(container_requester, http_cache_enabled):
    async with container_requester as requester:
        _, status, headers = await requester.make_request('GET', '/db/guillotina')
        assert status == 200

        assert 'Cache-Control' in headers
        assert headers['Cache-Control'] == 'max-age=123, public'
        assert 'ETag' in headers  # <-- it should be the transaction id


async def test_not_returned_in_default_post(container_requester, http_cache_enabled):
    async with container_requester as requester:
        _, status, headers = await requester.make_request(
            'POST', '/db/guillotina',
            data=json.dumps({
                "@type": "Item",
                "id": "myitem",
            })
        )
        assert status in [200, 201]
        assert 'Cache-Control' not in headers
        assert 'ETag' not in headers


async def test_not_returned_in_default_delete(container_requester, http_cache_enabled):
    async with container_requester as requester:
        _, status = await requester(
            'POST', '/db/guillotina',
            data=json.dumps({
                "@type": "Item",
                "id": "myitem",
            }))
        assert status in [200, 201]

        _, status, headers = await requester.make_request(
            'DELETE', '/db/guillotina/myitem')
        assert status == 200
        assert 'Cache-Control' not in headers
        assert 'ETag' not in headers


async def test_endpoint_specific_headers_supercedes_default(container_requester, http_cache_enabled):
    async with container_requester as requester:
        _, status, headers = await requester.make_request('GET', '/@testHttpCache')
        assert status == 200
        assert headers['Cache-Control'] == 'overwritten!'
        assert headers['Foo'] == 'Bar'
        assert 'ETag' in headers


async def test_endpoint_specific_from_dict(container_requester, http_cache_enabled):
    async with container_requester as requester:
        _, status, headers = await requester.make_request('POST', '/@testHttpCache')
        assert status == 200
        assert headers['from'] == 'a dictionary'

        # Test that default http headers are also there
        assert 'Cache-Control' in headers
        assert 'ETag' in headers
