from pytest_docker_fixtures import images


images.configure(
    'cockroach',
    'cockroachdb/cockroach', 'v2.1.6')


pytest_plugins = [
    'aiohttp.pytest_plugin',
    'guillotina.tests.fixtures'
]
