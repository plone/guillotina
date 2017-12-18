from guillotina.behaviors.attachment import IAttachment
from guillotina.tests import utils
from guillotina.transactions import managed_transaction

import json


async def test_create_content_with_behavior(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': ['guillotina.behaviors.attachment.IAttachment'],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar/@upload/file',
            data=b'X' * 1024 * 1024 * 4,
            headers={
                'x-upload-size': str(1024 * 1024 * 4)
            }
        )
        assert status == 200

        response, status = await requester(
            'GET',
            '/db/guillotina/foobar/@download/file'
        )
        assert status == 200
        assert len(response) == (1024 * 1024 * 4)


async def test_large_upload_chunks(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': ['guillotina.behaviors.attachment.IAttachment'],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar/@upload/file',
            data=b'X' * 1024 * 1024 * 10,
            headers={
                'x-upload-size': str(1024 * 1024 * 10)
            }
        )
        assert status == 200

        response, status = await requester(
            'GET',
            '/db/guillotina/foobar/@download/file'
        )
        assert status == 200
        assert len(response) == (1024 * 1024 * 10)

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('foobar')
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file._blob.chunks == 2


async def test_tus(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': ['guillotina.behaviors.attachment.IAttachment'],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'OPTIONS',
            '/db/guillotina/foobar/@tusupload/file')
        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'UPLOAD-LENGTH': str(1024 * 1024 * 10),
                'TUS-RESUMABLE': '1.0.0'
            }
        )
        assert status == 201

        response, status = await requester(
            'HEAD',
            '/db/guillotina/foobar/@tusupload/file')
        assert status == 200

        for idx in range(10):
            # 10, 1mb chunks
            response, status = await requester(
                'PATCH',
                '/db/guillotina/foobar/@tusupload/file',
                headers={
                    'CONTENT-LENGTH': str(1024 * 1024 * 1),
                    'TUS-RESUMABLE': '1.0.0',
                    'upload-offset': str(1024 * 1024 * idx)
                },
                data=b'X' * 1024 * 1024 * 1
            )
            assert status == 200

        response, status = await requester(
            'GET',
            '/db/guillotina/foobar/@download/file'
        )
        assert status == 200
        assert len(response) == (1024 * 1024 * 10)

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('foobar')
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file._blob.chunks == 10


async def test_copy_file_ob(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': ['guillotina.behaviors.attachment.IAttachment'],
                'id': 'foobar'
            })
        )
        assert status == 201
        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar/@upload/file',
            data=b'X' * 1024 * 1024 * 4,
            headers={
                'x-upload-size': str(1024 * 1024 * 4)
            }
        )
        assert status == 200

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('foobar')
            attachment = IAttachment(obj)
            await attachment.load()
            existing_bid = attachment.file._blob.bid
            await attachment.file.copy_cloud_file(obj)
            assert existing_bid != attachment.file._blob.bid
