import asyncio


async def test_install({{cookiecutter.package_name}}_requester):  # noqa
    async with {{cookiecutter.package_name}}_requester as requester:
        response, _ = await requester('GET', '/db/guillotina/@addons')
        assert '{{cookiecutter.package_name}}' in response['installed']
