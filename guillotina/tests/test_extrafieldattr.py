async def test_schema_extra(container_requester):
    async with container_requester as requester:
        resp, status = await requester(
            'GET',
            '/db/guillotina/@types/Example'
        )
        assert status == 200
        assert resp['properties']['textline_field']['widget'] == 'testing'
