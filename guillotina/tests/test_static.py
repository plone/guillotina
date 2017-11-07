from guillotina.component import get_utility
from guillotina.interfaces import IApplication


def test_get_static_folder(dummy_guillotina):
    root = get_utility(IApplication, name='root')
    assert 'static' in root._items


async def test_render_static_file(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/static/tests/teststatic.txt')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'


async def test_render_javascript_app(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/jsapp_static/teststatic.txt')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'


async def test_render_static_default_directory_file(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/static/tests')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'


async def test_render_jsapp_default_directory_file(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/jsapp_static')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'

        # and further down...
        response, status = await requester('GET', '/jsapp_static/foobar/foobar/foobar')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'


async def test_render_module_static_file(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/module_static/tests/teststatic.txt')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'


async def test_render_module_static_default_directory_file(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/module_static/tests')
        assert status == 200
        assert response.decode('utf8').strip() == 'foobar'
