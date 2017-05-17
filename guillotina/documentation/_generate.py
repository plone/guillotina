# this script requries the `requests` library to be installed in the environment
# which is no long a dependency of guillotina since it isn't used anywhere
# else.
from guillotina import app_settings
from guillotina import configure
from guillotina.addons import Addon
from guillotina.content import load_cached_schema
from guillotina.documentation import DIR
from guillotina.documentation import testmodule
from guillotina.documentation import URL
from guillotina.factory import make_app
from guillotina.testing import TESTING_SETTINGS
from guillotina.utils import get_dotted_name
from guillotina.utils import resolve_dotted_name

import json
import os
import requests


IGNORED_HEADERS = (
    'Accept-Encoding',
    'Connection',
    'User-Agent',
    'Date',
    'Access-Control-Allow-Credentials',
    'Access-Control-Expose-Headers',
    'Content-Length'
)

DEFAULT_HEADERS = {
    'Host': 'localhost:8080',
    'Accept': 'application/json'
}


BASE_PATHS = {
    '/': 'guillotina.interfaces.content.IApplication',
    '/db': 'guillotina.interfaces.content.IDatabase',
    '/db/container': 'guillotina.interfaces.content.IContainer',
    '/db/container/folder': 'guillotina.interfaces.content.IFolder',
    '/db/container/folder/item': 'guillotina.interfaces.content.IItem'
}


def write(name, data):
    filepath = os.path.join(DIR, name)
    fi = open(filepath, 'w')
    fi.write(data)
    fi.close()


def format_body(body):
    if body is None:
        return ''
    try:
        body = json.loads(body)
        return json.dumps(body, indent=4, sort_keys=True)
    except Exception:
        return body


def dump_request(req):
    return '{} HTTP/1.1\n{}\n\n{}'.format(
        req.method + ' ' + req.url.replace(URL, ''),
        '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()
                  if k not in IGNORED_HEADERS),
        format_body(req.body)
    )
    return


def dump_response(resp):
    return 'HTTP/1.1 {} {}\n{}\n\n{}'.format(
        resp.status_code, resp.reason,
        '\n'.join('{}: {}'.format(k, v) for k, v in resp.headers.items()
                  if k not in IGNORED_HEADERS),
        format_body(resp.text)
    )


def api(path, method='get', file_type_name=None, **kwargs):
    if path != '/':
        path = path.rstrip('/')

    service = get_service_def(path, method.upper())
    # path scheme used for things like traversing to registry value...
    name = service.get('name')
    path_scheme = kwargs.pop('path_scheme', name)

    print('Getting {} {}'.format(method, path))
    kwargs['auth'] = ('root', 'root')
    kwargs['headers'] = DEFAULT_HEADERS.copy()
    kwargs['headers'].update(kwargs.get('headers', {}))

    response = getattr(requests, method)(URL + path, **kwargs)

    iface = resolve_dotted_name(get_service_type_name(path)[-1])
    dotted = get_dotted_name(iface)
    data = {
        'path': path,
        'path_scheme': path_scheme,
        'method': method,
        'options': kwargs,
        'request': dump_request(response.request),
        'response': dump_response(response),
        'service': {
            'name': service.get('name'),
            'title': service.get('title'),
            'description': service.get('description'),
            'payload': service.get('payload'),
            'query_params': service.get('query_params'),
            'method': service.get('method', 'GET'),
            'context': get_dotted_name(iface),
            'permission': service.get('permission')
        }
    }

    if file_type_name is None:
        file_type_name = dotted.split('.')[-1][1:].lower()

    filepath = '{}/{}-{}'.format(DIR, file_type_name, method.lower())

    if path_scheme != name:
        # use special name here...
        name, _, rest = path_scheme.partition('/')
        filepath += '-{}:{}'.format(
            name.replace('@', ''),
            ''.join([l for l in rest.split(':')[0] if l not in '[]():-'])
        )
    elif service.get('name'):
        filepath += '-' + service.get('name').replace('@', '')

    filepath += '.json'
    fi = open(filepath, 'w')
    fi.write(json.dumps(data, indent=4, sort_keys=True))
    fi.close()


def get_type_services(iface):
    api_defs = app_settings['api_definition']
    for dotted_type in api_defs.keys():
        if iface == dotted_type:
            return api_defs[dotted_type]


def get_service_type_name(path):
    base_path, _, subpath = path.partition('@')
    if base_path != '/':
        base_path = base_path.rstrip('/')
    subpath = subpath.split('/')[0]  # could be traversing it...
    return base_path, subpath, BASE_PATHS[base_path]


def get_service_def(path, method=None, type_name=None):
    base_path, subpath, path_type_name = get_service_type_name(path)
    if type_name is not None:
        services = get_type_services(type_name)
    else:
        services = get_type_services(path_type_name)
    try:
        if '@' in path:
            return services['endpoints']['@' + subpath][method.upper()]
        else:
            return services[method]
    except (KeyError, TypeError):
        if type_name is not None:
            raise
        # this shouldn't happen, so we lookup other interfaces that this inherits
        # from to find service we're looking for
        iface = resolve_dotted_name(path_type_name)
        service = None
        for other_iface in iface.__bases__:
            try:
                service = get_service_def(path, method, get_dotted_name(other_iface))
            except (KeyError, TypeError):
                pass
            if service is not None:
                return service


class APIExplorer(object):
    def __init__(self, base_path='', type_name=None):
        self.base_path = base_path
        self.type_name = type_name

    def get(self, name='', **kwargs):
        api(os.path.join(self.base_path, name),
            file_type_name=self.type_name, **kwargs)
        return self

    def post(self, name='', jsond=None, **kwargs):
        api(os.path.join(self.base_path, name),
            'post', json=jsond, file_type_name=self.type_name, **kwargs)
        return self

    def patch(self, name='', jsond=None, **kwargs):
        api(os.path.join(self.base_path, name),
            'patch', json=jsond, file_type_name=self.type_name, **kwargs)
        return self

    def delete(self, name='', jsond=None, **kwargs):
        api(os.path.join(self.base_path, name),
            'delete', file_type_name=self.type_name, json=jsond, **kwargs)
        return self

    def options(self, name='', **kwargs):
        api(os.path.join(self.base_path, name),
            'options', file_type_name=self.type_name, **kwargs)
        return self

    def resource_api_basics(self):
        return self.get().get('@sharing').get('@all_permissions')\
            .get('@behaviors')


def setup_app():
    settings = TESTING_SETTINGS.copy()
    settings['applications'] = ['guillotina.documentation']
    aioapp = make_app(settings=settings)

    @configure.addon(
        name="myaddon",
        title="My addon")
    class MyAddon(Addon):

        @classmethod
        def install(cls, container, request):
            # install code
            pass

        @classmethod
        def uninstall(cls, container, request):
            # uninstall code
            pass

    config = aioapp.config
    configure.load_configuration(
        config, 'guillotina.documentation', 'addon')
    aioapp.config.execute_actions()
    load_cached_schema()


if __name__ == '__main__':
    setup_app()

    # application root
    APIExplorer('/').get().get('@apidefinition')

    # db root
    APIExplorer('/db').get().post(jsond={
        '@type': 'Container',
        'id': 'container',
        'title': 'Container'
    })

    # container root
    container_explorer = APIExplorer('/db/container')
    container_explorer.get().get('@types').post(jsond={
        '@type': 'Folder',
        'id': 'folder',
        'title': 'My Folder'
    })
    container_explorer.post('@addons', jsond={
        'id': 'myaddon'
    }).get('@addons').delete('@addons', jsond={
        'id': 'myaddon'
    })
    container_explorer.get('@registry').post(
        '@registry',
        jsond={
            'interface': get_dotted_name(testmodule.ISchema),
            'initial_values': {
                'foo': 'bar'
            }
        }
    ).patch('@registry/guillotina.documentation.testmodule.ISchema.foo',
            jsond={
                'value': 'New foobar value'
            },
            path_scheme='@registry/[dotted-name:string]').get(
        '@registry/guillotina.documentation.testmodule.ISchema.foo',
        path_scheme='@registry/[dotted-name:string]')

    # folder
    folder_explorer = APIExplorer('/db/container/folder', type_name='folder')
    folder_explorer.resource_api_basics().\
        patch(jsond={'title': 'My Folder Updated'}).\
        post(jsond={'@type': 'Item', 'id': 'item', 'title': 'My Item'})

    # item
    item_explorer = APIExplorer('/db/container/folder/item', type_name='item')
    item_explorer.resource_api_basics().\
        patch(jsond={'title': 'My Item Updated'}).\
        delete()

    # clean up...
    folder_explorer.delete()
    container_explorer.delete()
