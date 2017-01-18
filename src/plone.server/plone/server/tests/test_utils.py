from plone.server import utils


def test_module_resolve_path():
    assert utils.resolve_module_path('plone.server') == 'plone.server'
    assert utils.resolve_module_path('plone.server.tests') == 'plone.server.tests'
    assert utils.resolve_module_path('..test_queue') == 'plone.server.tests.test_queue'
    assert utils.resolve_module_path('....api') == 'plone.server.api'
