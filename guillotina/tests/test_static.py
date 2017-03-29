from guillotina.interfaces import IApplication
from guillotina.component import getUtility


def test_get_static_folder(dummy_guillotina):
    root = getUtility(IApplication, name='root')
    assert 'static' in root._items


async def test_render_static_file(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/static/tests/teststatic.txt')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'


async def test_render_static_default_directory_file(container_requester):
    async with await container_requester as requester:
        response, status = await requester('GET', '/static/tests')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'
