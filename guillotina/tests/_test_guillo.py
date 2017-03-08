# -*- encoding: utf-8 -*-
import json

async def test_get_the_root(guillotina):
    requester = await guillotina
    response, status = await requester('GET', '/')
    assert response['static_file'] == ['favicon.ico']
    assert response['databases'] == ['guillotina']
    assert response['static_directory'] == []


async def test_get_db(guillotina):
    requester = await guillotina
    response, status = await requester('GET', '/guillotina')
    assert response['sites'] == []


async def test_get_site(site):
    async for requester in site:
        response, status = await requester('GET', '/guillotina/guillotina')
        assert response['@type'] == 'Site'


async def test_get_content(site):
    async for requester in site:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina',
            data=json.dumps({
                '@type': 'Item',
                'id': 'hello',
                'title': 'Hola'
            }))
        assert status == 201
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/hello')
        assert status == 200


async def test_content_paths_are_correct(site):
    async for requester in site:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina',
            data=json.dumps({
                '@type': 'Item',
                'id': 'hello',
                'title': 'Hola'
            }))
        assert status == 201
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/hello')
        assert status == 200
        assert '/guillotina/guillotina/hello' in response['@id']
#
#
# async def test_serialize_behavior_annotation(dummy_txn_root, dummy_request, guillotina_main):
#     async for root in dummy_txn_root:
#         ob1 = Item()
#         await root.__setitem__('ob1', ob1)
#         dublin = IDublinCore(ob1)
#         await dublin.__setattr__('publisher', 'foobar')
#         serializer = getMultiAdapter(
#             (ob1, dummy_request),
#             IResourceSerializeToJson)
#         data = await serializer()
#         assert data['IDublinCore-publisher'] == 'foobar'
