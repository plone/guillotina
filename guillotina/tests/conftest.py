from pytest_docker_fixtures import images


images.configure(
    'cockroach',
    'cockroachdb/cockroach', 'v2.1.6')


pytest_plugins = [
    'guillotina.tests.fixtures'
]


def pytest_addoption(parser):
    parser.addoption(
        '--g-fast', action='store_true', default=False,
        help='run tests faster by disabling extra checks')
    parser.addoption(
        '--g-enable-loop-debug', action='store_true', default=False,
        help='enable event loop debug mode')
