from collections import OrderedDict
from plone.server import app_settings
from plone.server import metaconfigure
from plone.server.interfaces import DEFAULT_ADD_PERMISSION
from plone.server.interfaces import IDefaultLayer
from plone.server.interfaces import IResourceFactory
from plone.server.utils import caller_module
from plone.server.utils import resolve_or_get
from zope.component.zcml import utility
from zope.interface import classImplements
from zope.interface import Interface

import plone.behavior.metaconfigure


_registered_services = []
_registered_configurations = {
    'contenttypes': [],
    'behaviors': [],
    'addons': []
}


def register_service(view, func, config):
    config['factory'] = view
    _registered_services.append({
        'view': view,
        'func': func,
        'config': config
    })


def register_configuration(klass, config, type_):
    _registered_configurations[type_].append({
        'klass': klass,
        'config': config
    })


def _dotted_name(ob):
    return getattr(ob, '__module__', None) or getattr(ob, '__name__', '')


def get_services(module_name):
    results = []
    for service in _registered_services:
        if _dotted_name(service['func']).startswith(module_name):
            results.append(service)
    return results


def get_configurations(module_name, type_):
    results = []
    for contenttype in _registered_configurations[type_]:
        if _dotted_name(resolve_or_get(contenttype['klass'])).startswith(module_name):
            results.append(contenttype)
    return results


def load_services(_context, module_name):
    for service in get_services(module_name):
        service_conf = service['config']
        metaconfigure.register_service(
            _context,
            service_conf,
            service_conf['context'],
            service_conf.get('method', 'GET'),
            service_conf.get('layer', IDefaultLayer),
            service_conf.get('default_permission', app_settings['default_permission']),
            service_conf.get('name', '')
        )
        api = app_settings['api_definition']
        ct_name = service_conf['context'].__identifier__
        if ct_name not in api:
            api[ct_name] = OrderedDict()
        ct_api = api[ct_name]
        if service_conf.get('name', False):
            if 'endpoints' not in ct_api:
                ct_api['endpoints'] = OrderedDict()
            ct_api['endpoints'][service_conf.get('name')] = \
                OrderedDict(service_conf)
        else:
            ct_api[service_conf.get('method', 'GET')] = OrderedDict(service_conf)


def load_contenttypes(_context, module_name):
    for contenttype in get_configurations(module_name, 'contenttypes'):
        conf = contenttype['config']
        klass = contenttype['klass']
        if 'schema' in conf:
            classImplements(klass, conf['schema'])

        from plone.server.content import ResourceFactory

        factory = ResourceFactory(
            klass,
            title='',
            description='',
            portal_type=conf['portal_type'],
            schema=resolve_or_get(conf.get('schema', Interface)),
            behaviors=[resolve_or_get(b) for b in conf.get('behaviors', []) or ()],
            add_permission=conf.get('add_permission') or DEFAULT_ADD_PERMISSION,
            allowed_types=conf.get('allowed_types', None)
        )
        utility(
            _context,
            provides=IResourceFactory,
            component=factory,
            name=conf['portal_type'],
        )


def load_behaviors(_context, module_name):
    for behavior in get_configurations(module_name, 'behaviors'):
        conf = behavior['config']
        klass = resolve_or_get(behavior['klass'])
        factory = conf.get('factory') or klass
        plone.behavior.metaconfigure.behaviorDirective(
            _context,
            conf.get('title', ''),
            resolve_or_get(conf['provides']),
            name=conf.get('name'),
            description=conf.get('description'),
            marker=resolve_or_get(conf.get('marker')),
            factory=resolve_or_get(factory),
            for_=resolve_or_get(conf.get('for_')),
            name_only=conf.get('name_only')
        )


def load_addons(_context, module_name):
    for addon in get_configurations(module_name, 'addons'):
        config = addon['config']
        app_settings['available_addons'][config['name']] = {
            'title': config['title'],
            'handler': addon['klass']
        }


class _base_configuration(object):
    configuration_type = ''

    def __init__(self, **config):
        self.config = config

    def __call__(self, klass):
        register_configuration(klass, self.config, self.configuration_type)
        return klass


class service(_base_configuration):
    """
    service decorator to be able to provide functions for services.

    @service()
    async def my_service(context, request):
        pass

    """
    def __call__(self, func):
        if isinstance(func, type):
            # it is a class view, we don't need to generate one for it...
            register_service(func, func, self.config)
            return func
        else:
            # avoid circular imports
            from plone.server.api.service import Service

            class _View(self.config.get('base', Service)):
                async def __call__(self):
                    return await func(self.context, self.request)

            register_service(_View, func, self.config)
            return _View


class contenttype(_base_configuration):
    """
    content type decorator

    @contenttype()
    class MyContent(Item):
        pass

    """
    configuration_type = 'contenttypes'


class behavior(_base_configuration):
    """
    behavior decorator

    @contenttype()
    class MyContent(Item):
        pass

    """
    configuration_type = 'behaviors'

    def __call__(self, klass=None):
        if klass is None:
            if 'factory' not in self.config:
                raise Exception('Must provide factory configuration when defining '
                                'a behavior with no class')
            klass = caller_module()
        return super(behavior, self).__call__(klass)


class addon(_base_configuration):
    """
    addon decorator
    """
    configuration_type = 'addons'


def scan(path):
    """
    pyramid's version of scan has a much more advanced resolver that we
    can look into supporting eventually...
    """
    __import__(path)
