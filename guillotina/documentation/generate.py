# this script requries the `requests` library to be installed in the environment
# which is no long a dependency of guillotina since it isn't used anywhere
# else.
from guillotina._settings import app_settings
from guillotina.component import get_utility
from guillotina.interfaces import IResourceFactory
from guillotina.tests.utils import create_content
from guillotina.utils import get_dotted_name
from guillotina.utils import resolve_dotted_name
from urllib.parse import urlparse

import os
import requests
import ujson


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


# XXX
BASE_PATHS = {
    '/': 'guillotina.interfaces.content.IApplication',
    '/db': 'guillotina.interfaces.content.IDatabase',
    '/db/container': 'guillotina.interfaces.content.IContainer',
    '/db/container/folder': 'guillotina.interfaces.content.IFolder',
    '/db/container/folder/item': 'guillotina.interfaces.content.IItem'
}


class Generator:

    def __init__(self, base_url, output_dir):
        self._base_url = base_url
        self._output_dir = output_dir
        self._cached_type_names = {}

    def write(self, name, data):
        filepath = os.path.join(self._output_dir, name)
        fi = open(filepath, 'w')
        fi.write(data)
        fi.close()

    def format_body(self, body):
        if body is None:
            return ''
        try:
            body = ujson.loads(body)
            return ujson.dumps(body, indent=4, sort_keys=True)
        except Exception:
            return body

    def dump_request(self, req):
        return '{} HTTP/1.1\n{}\n\n{}'.format(
            req.method + ' ' + req.url.replace(self._base_url, ''),
            '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()
                      if k not in IGNORED_HEADERS),
            self.format_body(req.body)
        )
        return

    def dump_response(self, resp):
        return 'HTTP/1.1 {} {}\n{}\n\n{}'.format(
            resp.status_code, resp.reason,
            '\n'.join('{}: {}'.format(k, v) for k, v in resp.headers.items()
                      if k not in IGNORED_HEADERS),
            self.format_body(resp.text)
        )

    def _get_stub_content(self, url):
        type_name = self._get_type_name(url)
        rfactory = get_utility(IResourceFactory, name=type_name)
        return create_content(rfactory._callable, type_name)

    def _function_swagger_param(self, data, url):
        if callable(data):
            data = data(self._get_stub_content(url))
        return data

    def _get_normalized_path(self, url):
        if 'http://' in url or 'https://' in url:
            parsed = urlparse(url)
            url = parsed.path
        return url.split('/@')[0] or '/'

    def _get_type_name(self, url):
        path = self._get_normalized_path(url)
        if path in self._cached_type_names:
            return self._cached_type_names[path]

    def _store_type_name(self, response, url, url_options):
        path = self._get_normalized_path(url)
        if path in self._cached_type_names:
            return

        try:
            response_data = response.json()
            if '@type' in response_data:
                self._cached_type_names[path] = response_data['@type']
        except Exception:
            pass
        if url in self._cached_type_names:
            return
        # still don't have it, get the content manually...
        response = requests.get(url, **url_options)
        response_content = response.json()
        try:
            self._cached_type_names[path] = response_content['@type']
        except Exception:
            # no type for this... it's okay, probably root or db
            self._cached_type_names[path] = 'Unknown'

    def api(self, path, method='get', file_type_name=None, **kwargs):
        if path != '/':
            path = path.rstrip('/')

        print('Getting {} {}'.format(method, path))
        kwargs['auth'] = ('root', 'root')
        kwargs['headers'] = DEFAULT_HEADERS.copy()
        kwargs['headers'].update(kwargs.get('headers', {}))

        url = self._base_url + path
        response = getattr(requests, method)(url, **kwargs)
        self._store_type_name(response, url, kwargs)

        service = self.get_service_def(path, method.upper())
        # path scheme used for things like traversing to registry value...
        name = service.get('name')
        path_scheme = kwargs.pop('path_scheme', name)

        iface = resolve_dotted_name(self.get_service_type_name(path)[-1])
        dotted = get_dotted_name(iface)
        responses = self._function_swagger_param(service.get('responses'), url)
        parameters = self._function_swagger_param(service.get('parameters'), url)
        data = {
            'path': path,
            'path_scheme': path_scheme,
            'method': method,
            'options': kwargs,
            'request': self.dump_request(response.request),
            'response': self.dump_response(response),
            'service': {
                'name': service.get('name'),
                'title': service.get('title'),
                'summary': service.get('summary'),
                'parameters': parameters,
                'responses': responses,
                'method': service.get('method', 'GET'),
                'context': get_dotted_name(iface),
                'permission': service.get('permission')
            }
        }

        if file_type_name is None:
            file_type_name = dotted.split('.')[-1][1:].lower()

        filepath = '{}/{}-{}'.format(self._output_dir, file_type_name, method.lower())

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
        fi.write(ujson.dumps(data, indent=4, sort_keys=True))
        fi.close()

    def get_type_services(self, iface):
        api_defs = app_settings['api_definition']
        for dotted_type in api_defs.keys():
            if iface == dotted_type:
                return api_defs[dotted_type]

    def get_service_type_name(self, path):
        base_path, _, subpath = path.partition('@')
        if base_path != '/':
            base_path = base_path.rstrip('/')
        subpath = subpath.split('/')[0]  # could be traversing it...

        type_name = self._get_type_name(path)
        if type_name == 'Application':
            iface = 'guillotina.interfaces.content.IApplication'
        elif type_name == 'Database':
            iface = 'guillotina.interfaces.content.IDatabase'
        else:
            type_name = self._get_type_name(path)
            rfactory = get_utility(IResourceFactory, name=type_name)
            iface = get_dotted_name(rfactory.schema)
        return base_path, subpath, iface

    def get_service_def(self, path, method=None, type_name=None):
        base_path, subpath, path_type_name = self.get_service_type_name(path)
        if type_name is not None:
            services = self.get_type_services(type_name)
        else:
            services = self.get_type_services(path_type_name)
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
                    service = self.get_service_def(path, method, get_dotted_name(other_iface))
                except (KeyError, TypeError):
                    pass
                if service is not None:
                    return service


class APIExplorer(object):
    def __init__(self, generator, base_path='', type_name=None):
        self._generator = generator
        self._base_path = base_path
        self._type_name = type_name

    def get(self, path='', **kwargs):
        self._generator.api(
            os.path.join(self._base_path, path),
            file_type_name=self._type_name, **kwargs)
        return self

    def post(self, path='', jsond=None, **kwargs):
        self._generator.api(
            os.path.join(self._base_path, path),
            'post', json=jsond, file_type_name=self._type_name, **kwargs)
        return self

    def patch(self, path='', jsond=None, **kwargs):
        self._generator.api(
            os.path.join(self._base_path, path),
            'patch', json=jsond, file_type_name=self._type_name, **kwargs)
        return self

    def delete(self, path='', jsond=None, **kwargs):
        self._generator.api(
            os.path.join(self._base_path, path),
            'delete', file_type_name=self._type_name, json=jsond, **kwargs)
        return self

    def options(self, path='', **kwargs):
        self._generator.api(
            os.path.join(self._base_path, path),
            'options', file_type_name=self._type_name, **kwargs)
        return self


def process_command_file(filepath, base_url, output_dir):
    with open(filepath) as fi:
        commands = ujson.loads(fi.read())
    generator = Generator(base_url, output_dir)
    for command in commands:
        explorer = APIExplorer(generator, command.get("path"), command.get('type_name'))
        for action in command['actions']:
            method = action.pop('method', 'get').lower()
            func = getattr(explorer, method, None)
            if func is None:
                raise Exception(f'Invalid method {method} for {ujson.dumps(action)}')
            func(**action)
