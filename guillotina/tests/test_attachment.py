from guillotina.behaviors.attachment import IAttachment
from guillotina.component import get_multi_adapter
from guillotina.interfaces import IFileManager
from guillotina.tests import utils
from guillotina.transactions import managed_transaction

import json
import random


async def test_create_content_with_behavior(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': [IAttachment.__identifier__],
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
                '@behaviors': [IAttachment.__identifier__],
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
                '@behaviors': [IAttachment.__identifier__],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'OPTIONS',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Origin': 'http://foobar.com',
                'Access-Control-Request-Method': 'POST'
            })
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


async def test_tus_unknown_size(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': [IAttachment.__identifier__],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'OPTIONS',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Origin': 'http://foobar.com',
                'Access-Control-Request-Method': 'POST'
            })
        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Upload-Defer-Length': '1',
                'TUS-RESUMABLE': '1.0.0'
            }
        )
        assert status == 201

        response, status = await requester(
            'HEAD',
            '/db/guillotina/foobar/@tusupload/file')
        assert status == 200

        offset = 0
        for idx in range(10):
            # random sizes
            size = 1024 * random.choice([1024, 1243, 5555, 7777])
            response, status = await requester(
                'PATCH',
                '/db/guillotina/foobar/@tusupload/file',
                headers={
                    'TUS-RESUMABLE': '1.0.0',
                    'upload-offset': str(offset)
                },
                data=b'X' * size
            )
            offset += size
            assert status == 200

        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'TUS-RESUMABLE': '1.0.0',
                'upload-offset': str(offset),
                'UPLOAD-LENGTH': str(offset)  # finish it
            },
            data=b''
        )

        response, status = await requester(
            'GET',
            '/db/guillotina/foobar/@download/file'
        )
        assert status == 200
        assert len(response) == offset

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('foobar')
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file._blob.size == offset


async def test_copy_file_ob(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': [IAttachment.__identifier__],
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
            cfm = get_multi_adapter(
                (obj, request, IAttachment['file'].bind(attachment)), IFileManager
            )
            from_cfm = get_multi_adapter(
                (obj, request, IAttachment['file'].bind(attachment)), IFileManager
            )
            await cfm.copy(from_cfm)
            assert existing_bid != attachment.file._blob.bid


async def test_tus_unfinished_error(container_requester):
    async with container_requester as requester:
        _, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': [IAttachment.__identifier__],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'OPTIONS',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Origin': 'http://foobar.com',
                'Access-Control-Request-Method': 'POST'
            })
        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Upload-Length': '1024',
                'TUS-RESUMABLE': '1.0.0'
            }
        )
        assert status == 201

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Upload-Length': '1024',
                'TUS-RESUMABLE': '1.0.0'
            }
        )
        # upload already started, should error
        assert status == 412

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Upload-Length': '1024',
                'TUS-RESUMABLE': '1.0.0',
                'TUS-OVERRIDE-UPLOAD': '1'
            }
        )
        # override it
        assert status == 201


async def test_tus_with_empty_file(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': [IAttachment.__identifier__],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'OPTIONS',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'Origin': 'http://foobar.com',
                'Access-Control-Request-Method': 'POST'
            })
        assert status == 200

        response, status = await requester(
            'POST',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'UPLOAD-LENGTH': '0',
                'TUS-RESUMABLE': '1.0.0'
            }
        )
        assert status == 201

        response, status = await requester(
            'HEAD',
            '/db/guillotina/foobar/@tusupload/file')
        assert status == 200

        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar/@tusupload/file',
            headers={
                'CONTENT-LENGTH': '0',
                'TUS-RESUMABLE': '1.0.0',
                'upload-offset': '0'
            },
            data=b''
        )
        assert status == 200

        response, status = await requester(
            'GET',
            '/db/guillotina/foobar/@download/file'
        )
        assert status == 200
        assert len(response) == 0

        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        async with managed_transaction(request=request, abort_when_done=True):
            container = await root.async_get('guillotina')
            obj = await container.async_get('foobar')
            behavior = IAttachment(obj)
            await behavior.load()
            assert behavior.file._blob.chunks == 0


async def test_update_filename_on_files(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina/',
            data=json.dumps({
                '@type': 'Item',
                '@behaviors': [IAttachment.__identifier__],
                'id': 'foobar'
            })
        )
        assert status == 201

        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar/@upload/file',
            data=b'X' * 1024 * 1024,
            headers={
                'x-upload-size': str(1024 * 1024)
            }
        )
        assert status == 200

        response, status = await requester(
            'PATCH',
            '/db/guillotina/foobar',
            data=json.dumps({
                IAttachment.__identifier__: {
                    "file": {
                        "filename": "foobar.jpg",
                        "content_type": "image/jpeg",
                        "md5": 'foobar',
                        'extension': 'jpg'
                    }
                }
            })
        )

        response, status = await requester('GET', '/db/guillotina/foobar')
        data = response[IAttachment.__identifier__]['file']
        assert data['filename'] == 'foobar.jpg'
        assert data['content_type'] == 'image/jpeg'
        assert data['md5'] == 'foobar'
        assert data['extension'] == 'jpg'
