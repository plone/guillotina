pytest_plugins = [
    'aiohttp.pytest_plugin',
    'guillotina.tests.fixtures',
    '{{cookiecutter.package_name}}.tests.fixtures'
]
