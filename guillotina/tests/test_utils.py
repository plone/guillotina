from guillotina import utils


def test_module_resolve_path():
    assert utils.resolve_module_path('guillotina') == 'guillotina'
    assert utils.resolve_module_path('guillotina.tests') == 'guillotina.tests'
    assert utils.resolve_module_path('..test_queue') == 'guillotina.tests.test_queue'
    assert utils.resolve_module_path('....api') == 'guillotina.api'
