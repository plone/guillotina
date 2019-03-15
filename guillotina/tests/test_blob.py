from guillotina.blob import Blob
from guillotina.component import get_utility
from guillotina.content import create_content_in_container
from guillotina.interfaces import IApplication
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login
from guillotina.transactions import managed_transaction


async def test_create_blob(db, guillotina_main):
    root = get_utility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    async with managed_transaction(request=request):
        container = await create_content_in_container(
            db, 'Container', 'container', request=request,
            title='Container')

        blob = Blob(container)
        container.blob = blob

    async with managed_transaction(request=request):
        container = await db.async_get('container')
        assert blob.bid == container.blob.bid
        assert blob.resource_zoid == container._p_oid
        await db.async_del('container')


async def test_write_blob_data(db, guillotina_main):
    root = get_utility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    async with managed_transaction(request=request):
        container = await db.async_get('container')
        if container is None:
            container = await create_content_in_container(
                db, 'Container', 'container', request=request,
                title='Container')

        blob = Blob(container)
        container.blob = blob

        blobfi = blob.open('w')
        await blobfi.async_write(b'foobar')

    async with managed_transaction(request=request):
        container = await db.async_get('container')
        assert await container.blob.open().async_read() == b'foobar'
        assert container.blob.size == 6
        assert container.blob.chunks == 1

        await db.async_del('container')


async def test_write_large_blob_data(db, guillotina_main):
    root = get_utility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    async with managed_transaction(request=request):
        container = await db.async_get('container')
        if container is None:
            container = await create_content_in_container(
                db, 'Container', 'container', request=request,
                title='Container')

        blob = Blob(container)
        container.blob = blob

        multiplier = 999999

        blobfi = blob.open('w')
        await blobfi.async_write(b'foobar' * multiplier)

    async with managed_transaction(request=request):
        container = await db.async_get('container')
        assert await container.blob.open().async_read() == (b'foobar' * multiplier)
        assert container.blob.size == len(b'foobar' * multiplier)
        assert container.blob.chunks == 6

        await db.async_del('container')
