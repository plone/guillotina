from collections import OrderedDict
from plone.server import metaconfigure
from plone.server.interfaces import DEFAULT_ADD_PERMISSION
from plone.server.interfaces import IDefaultLayer
from plone.server.interfaces import IResourceFactory
from plone.server.utils import caller_module
from plone.server.utils import dotted_name
from plone.server.utils import resolve_module_path
from plone.server.utils import resolve_or_get
from zope.component import zcml
from zope.interface import classImplements
from zope.interface import Interface
from zope.configuration import xmlconfig

import plone.behavior.metaconfigure
import zope.security.zcml
import zope.securitypolicy.metaconfigure


_registered_configurations = []
# stored as tuple of (type, configuration) so we get keep it in the order
# it is registered even if you mix types of registrations

_registered_configuration_handlers = {}


def get_configurations(module_name, type_=None):
    results = []
    for reg_type, registration in _registered_configurations:
        if type_ is not None and reg_type != type_:
            continue
        config = registration['config']
        module = config.get('module', registration.get('klass'))
        if dotted_name(resolve_or_get(module)).startswith(module_name):
            results.append((reg_type, registration))
    return results


def register_configuration_handler(type_, handler):
    _registered_configuration_handlers[type_] = handler


def register_configuration(klass, config, type_):
    _registered_configurations.append((type_, {
        'klass': klass,
        'config': config
    }))


def load_configuration(_context, module_name, _type):
    if _type not in _registered_configuration_handlers:
        raise Exception('Configuration handler for {} not registered'.format(_type))
    for _type, configuration in get_configurations(module_name, _type):
        _registered_configuration_handlers[_type](_context, configuration)


def load_all_configurations(_context, module_name):
    for type_, configuration in get_configurations(module_name):
        _registered_configuration_handlers[type_](_context, configuration)


def load_service(_context, service):
    from plone.server import app_settings

    service_conf = service['config']
    service_conf['factory'] = service['klass']
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
register_configuration_handler('service', load_service)


def load_contenttype(_context, contenttype):
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
    zcml.utility(
        _context,
        provides=IResourceFactory,
        component=factory,
        name=conf['portal_type'],
    )
register_configuration_handler('contenttype', load_contenttype)


def load_behavior(_context, behavior):
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
register_configuration_handler('behavior', load_behavior)


def load_addon(_context, addon):
    from plone.server import app_settings
    config = addon['config']
    app_settings['available_addons'][config['name']] = {
        'title': config['title'],
        'handler': addon['klass']
    }
register_configuration_handler('addon', load_addon)


def _component_conf(conf):
    if type(conf['for_']) not in (tuple, set, list):
        conf['for_'] = (conf['for_'],)


def load_adapter(_context, adapter):
    conf = adapter['config']
    klass = resolve_or_get(adapter['klass'])
    factory = conf.pop('factory', None) or klass
    _component_conf(conf)
    if 'provides' in conf and isinstance(klass, type):
        # not sure if this is what we want or not for sure but
        # we are automatically applying the provides interface to
        # registered class objects
        classImplements(klass, conf['provides'])
    zcml.adapter(
        _context,
        factory=(factory,),
        **conf
    )
register_configuration_handler('adapter', load_adapter)


def load_subscriber(_context, subscriber):
    conf = subscriber['config']
    conf['handler'] = resolve_or_get(conf.get('handler') or subscriber['klass'])
    _component_conf(conf)
    zcml.subscriber(
        _context,
        **conf
    )
register_configuration_handler('subscriber', load_subscriber)


def load_utility(_context, _utility):
    conf = _utility['config']
    if 'factory' in conf:
        conf['factory'] = resolve_or_get(conf['factory'])
    elif 'component' in conf:
        conf['component'] = resolve_or_get(conf['component'])
    else:
        # use provided klass
        klass = _utility['klass']
        if isinstance(klass, type):
            # is a class type, use factory setting
            conf['factory'] = klass
        else:
            # not a factory
            conf['component'] = klass
    zcml.utility(
        _context,
        **conf
    )
register_configuration_handler('utility', load_utility)


def load_permission(_context, permission):
    zope.security.zcml.permission(_context, **permission['config'])
register_configuration_handler('permission', load_permission)


def load_role(_context, role):
    zope.securitypolicy.metaconfigure.defineRole(_context, **role['config'])
register_configuration_handler('role', load_role)


def load_grant(_context, grant):
    zope.securitypolicy.metaconfigure.grant(_context, **grant['config'])
register_configuration_handler('grant', load_grant)


def load_grant_all(_context, grant_all):
    zope.securitypolicy.metaconfigure.grantAll(_context, **grant_all['config'])
register_configuration_handler('grant_all', load_grant_all)


def load_include(_context, _include):
    config = _include['config']
    if 'package' in config:
        config['package'] = resolve_or_get(
            resolve_module_path(config['package']))
    xmlconfig.include(_context, **config)
register_configuration_handler('include', load_include)


class _base_decorator(object):
    configuration_type = ''

    def __init__(self, **config):
        self.config = config

    def __call__(self, klass):
        register_configuration(klass, self.config, self.configuration_type)
        return klass


class _factory_decorator(_base_decorator):
    """
    behavior that can pass factory to it so it can be used standalone
    """

    def __call__(self, klass=None):
        if klass is None:
            if 'factory' not in self.config:
                raise Exception('Must provide factory configuration when defining '
                                'without a class')
            klass = caller_module()
        return super(_factory_decorator, self).__call__(klass)


class service(_base_decorator):
    def __call__(self, func):
        if isinstance(func, type):
            # it is a class view, we don't need to generate one for it...
            register_configuration(func, self.config, 'service')
            return func
        else:
            # avoid circular imports
            from plone.server.api.service import Service

            class _View(self.config.get('base', Service)):
                async def __call__(self):
                    return await func(self.context, self.request)

            self.config['module'] = func
            register_configuration(_View, self.config, 'service')
            return _View


class contenttype(_base_decorator):
    configuration_type = 'contenttype'


class behavior(_factory_decorator):
    configuration_type = 'behavior'


class addon(_base_decorator):
    configuration_type = 'addon'


class adapter(_factory_decorator):
    configuration_type = 'adapter'


class subscriber(_factory_decorator):
    configuration_type = 'subscriber'


class utility(_factory_decorator):
    configuration_type = 'utility'


def permission(id, title, description=''):
    register_configuration(
        caller_module(),
        dict(
            id=id,
            title=title,
            description=description),
        'permission')


def role(id, title, description=''):
    register_configuration(
        caller_module(),
        dict(
            id=id,
            title=title,
            description=description),
        'role')


def grant(principal=None, role=None, permission=None,
          permissions=None):
    register_configuration(
        caller_module(),
        dict(
            principal=principal,
            role=role,
            permission=permission,
            permissions=permissions),
        'grant')


def grant_all(principal=None, role=None):
    register_configuration(
        caller_module(),
        dict(
            principal=principal,
            role=role),
        'grant_all')


def include(package, file=None):
    """
    include is different from scan. Include is for including a regular zcml
    include
    """
    register_configuration(
        caller_module(),
        dict(package=package, file=file),
        'include')


def scan(path):
    """
    pyramid's version of scan has a much more advanced resolver that we
    can look into supporting eventually...
    """
    path = resolve_module_path(path)
    __import__(path)


def clear():
    _registered_configurations[:] = []
