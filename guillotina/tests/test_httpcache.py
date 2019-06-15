async def test_response_headers_are_added(container_requester, http_cache_enabled):
    async with container_requester as requester:
        _, status, headers = await requester.make_request('GET', '/@testit')
        assert status == 200

        assert 'Cache-Control' in headers
        assert headers['Cache-Control'] == 'max-age=123, public'
        assert 'ETag' in headers
        assert headers['Etag'] == 'foobar'


async def test_response_headers_are_only_added_on_get_requests(container_requester, http_cache_enabled):
    async with container_requester as requester:
        for method in ('POST', 'HEAD', 'DELETE'):
            _, status, headers = await requester.make_request(method, '/@testit')
            assert status == 200
            assert 'Cache-Control' not in headers
            assert 'ETag' not in headers
