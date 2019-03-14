from guillotina.annotations import AnnotationData
from guillotina.component import get_utility
from guillotina.content import create_content_in_container
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IApplication
from guillotina.tests.utils import get_mocked_request
from guillotina.tests.utils import login
from guillotina.transactions import managed_transaction


async def test_create_annotation(db, guillotina_main):
    root = get_utility(IApplication, name='root')
    db = root['db']
    request = get_mocked_request(db)
    login(request)

    async with managed_transaction(request=request, write=True):
        container = await create_content_in_container(
            db, 'Container', 'container', request=request,
            title='Container')
        ob = await create_content_in_container(
            container, 'Item', 'foobar', request=request)

        annotations = IAnnotations(ob)
        data = AnnotationData()
        data['foo'] = 'bar'
        await annotations.async_set('foobar', data)

    async with managed_transaction(request=request, write=True):
        container = await db.async_get('container')
        ob = await container.async_get('foobar')
        annotations = IAnnotations(ob)
        assert 'foobar' in (await annotations.async_keys())
        await annotations.async_del('foobar')

    async with managed_transaction(request=request, write=True):
        container = await db.async_get('container')
        ob = await container.async_get('foobar')
        annotations = IAnnotations(ob)
        assert 'foobar' not in (await annotations.async_keys())
        await container.async_del('foobar')
        await db.async_del('container')
