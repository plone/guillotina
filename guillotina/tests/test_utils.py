from guillotina import utils


def test_module_resolve_path():
    assert utils.resolve_module_path('guillotina') == 'guillotina'
    assert utils.resolve_module_path('guillotina.tests') == 'guillotina.tests'
    assert utils.resolve_module_path('..test_queue') == 'guillotina.tests.test_queue'
    assert utils.resolve_module_path('....api') == 'guillotina.api'


class FooBar(object):
    pass


def test_dotted_name():
    assert utils.get_class_dotted_name(FooBar()) == 'guillotina.tests.test_utils.FooBar'
    assert utils.get_class_dotted_name(FooBar) == 'guillotina.tests.test_utils.FooBar'
    assert utils.get_module_dotted_name(FooBar()) == 'guillotina.tests.test_utils'
    assert utils.get_module_dotted_name(FooBar) == 'guillotina.tests.test_utils'
