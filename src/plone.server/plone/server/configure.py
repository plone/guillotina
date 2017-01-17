from collections import OrderedDict
from plone.server import app_settings
from plone.server import metaconfigure
from plone.server.interfaces import IDefaultLayer


_registered_services = []


def register_service(view, func, config):
    config['factory'] = view
    _registered_services.append({
        'view': view,
        'func': func,
        'config': config
    })


def get_services(module_name):
    results = []
    for service in _registered_services:
        if service['func'].__module__.startswith(module_name):
            results.append(service)
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


class service(object):
    """
    service decorator to be able to provide functions for services.

    @service()
    async def my_service(context, request):
        pass

    """

    def __init__(self, **config):
        self.config = config

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
