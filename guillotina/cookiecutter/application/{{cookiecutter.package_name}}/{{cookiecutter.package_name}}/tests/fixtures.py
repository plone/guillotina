from guillotina import testing
from guillotina.tests.fixtures import ContainerRequesterAsyncContextManager

import json
import pytest


def base_settings_configurator(settings):
    if 'applications' in settings:
        settings['applications'].append('{{cookiecutter.package_name}}')
    else:
        settings['applications'] = ['{{cookiecutter.package_name}}']


testing.configure_with(base_settings_configurator)


class {{cookiecutter.package_name}}_Requester(ContainerRequesterAsyncContextManager):  # noqa

    async def __aenter__(self):
        await super().__aenter__()
        resp = await self.requester(
            'POST', '/db/guillotina/@addons',
            data=json.dumps({
                'id': '{{cookiecutter.package_name}}'
            })
        )
        return self.requester


@pytest.fixture(scope='function')
async def {{cookiecutter.package_name}}_requester(guillotina):
    return {{cookiecutter.package_name}}_Requester(guillotina)
