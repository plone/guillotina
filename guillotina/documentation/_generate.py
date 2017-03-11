from guillotina import app_settings
from guillotina.content import load_cached_schema
from guillotina.documentation import DIR
from guillotina.documentation import URL
from guillotina.factory import make_app
from guillotina.testing import TESTING_SETTINGS
from guillotina.utils import get_class_dotted_name
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
    'Access-Control-Expose-Headers'
)

DEFAULT_HEADERS = {
    'Host': 'localhost:8080',
    'Accept': 'application/json'
}


BASE_PATHS = {
    '/': 'guillotina.interfaces.content.IApplication',
    '/db': 'guillotina.interfaces.content.IDatabase',
    '/db/site': 'guillotina.interfaces.content.ISite',
    '/db/site/folder': 'guillotina.interfaces.content.IContainer',
    '/db/site/folder/item': 'guillotina.interfaces.content.IItem'
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
    except:
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
    print('Getting {} {}'.format(method, path))
    kwargs['auth'] = ('root', 'root')
    kwargs['headers'] = DEFAULT_HEADERS.copy()
    kwargs['headers'].update(kwargs.get('headers', {}))

    response = getattr(requests, method)(URL + path, **kwargs)

    service = get_service_def(path, method.upper())
    iface = resolve_dotted_name(get_service_type_name(path)[-1])
    dotted = get_class_dotted_name(iface)
    data = {
        'path': path,
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
            'context': get_class_dotted_name(iface),
            'permission': service.get('permission')
        }
    }

    if file_type_name is None:
        file_type_name = dotted.split('.')[-1][1:].lower()

    filepath = '{}/{}-{}'.format(DIR, file_type_name, method.lower())

    if service.get('name'):
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
    return base_path, subpath, BASE_PATHS[base_path]


def get_service_def(path, method=None, type_name=None):
    base_path, subpath, path_type_name = get_service_type_name(path)
    if type_name is not None:
        services = get_type_services(type_name)
    else:
        services = get_type_services(path_type_name)
    try:
        if '@' in path:
            return services['endpoints']['@' + subpath]
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
                service = get_service_def(path, method, get_class_dotted_name(other_iface))
            except (KeyError, TypeError):
                pass
            if service is not None:
                return service


class APIExplorer(object):
    def __init__(self, base_path='', type_name=None):
        self.base_path = base_path
        self.type_name = type_name

    def get(self, name=''):
        api(os.path.join(self.base_path, name),
            file_type_name=self.type_name)
        return self

    def post(self, jsond, name=''):
        api(os.path.join(self.base_path, name),
            'post', json=jsond, file_type_name=self.type_name)
        return self

    def patch(self, jsond, name=''):
        api(os.path.join(self.base_path, name),
            'patch', json=jsond, file_type_name=self.type_name)
        return self

    def delete(self, name=''):
        api(os.path.join(self.base_path, name),
            'delete', file_type_name=self.type_name)
        return self

    def options(self, name=''):
        api(os.path.join(self.base_path, name),
            'options', file_type_name=self.type_name)
        return self


if __name__ == '__main__':
    aioapp = make_app(settings=TESTING_SETTINGS)
    aioapp.config.execute_actions()
    load_cached_schema()

    # application root
    APIExplorer('/').get().get('@apidefinition')

    # db root
    APIExplorer('/db').get().post(jsond={
        '@type': 'Site',
        'id': 'site',
        'title': 'Site'
    })

    # site root
    site_explorer = APIExplorer('/db/site')
    site_explorer.get().options().get('@addons').get('@registry')\
        .get('@types').post(jsond={
            '@type': 'Folder',
            'id': 'folder',
            'title': 'My Folder'
        })

    # folder
    folder_explorer = APIExplorer('/db/site/folder', type_name='folder')
    folder_explorer.get().options().get('@sharing').get('@all_permissions')\
        .get('@behaviors').patch(jsond={
            'title': 'My Folder Updated'
        }).post(jsond={
            '@type': 'Item',
            'id': 'item',
            'title': 'My Item'
        })

    # item
    item_explorer = APIExplorer('/db/site/folder/item', type_name='item')
    item_explorer.get().options().get('@sharing').get('@all_permissions')\
        .get('@behaviors').patch(jsond={
            'title': 'My Item Updated'
        }).delete()

    # clean up...
    folder_explorer.delete()
    site_explorer.delete()
