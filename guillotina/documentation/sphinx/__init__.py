# -*- coding: utf-8 -*-
from guillotina import routes
from aiohttp.test_utils import TestClient
from aiohttp.test_utils import TestServer
from base64 import b64encode
from guillotina.component import query_multi_adapter
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst import directives  # type: ignore
from guillotina.content import load_cached_schema
from guillotina.factory import make_app
from guillotina.tests.utils import get_mocked_request
from guillotina.transactions import abort
from guillotina._settings import app_settings
from guillotina.utils import get_dotted_name
import asyncio
import json
import pkg_resources
from guillotina.traversal import traverse

_server = None

IGNORED_HEADERS = (
    'Accept-Encoding',
    'Connection',
    'User-Agent',
    'Date',
    'Access-Control-Allow-Credentials',
    'Access-Control-Expose-Headers',
    'Server'
)


def get_server():
    global _server
    if _server is not None:
        return _server

    loop = asyncio.new_event_loop()
    aioapp = make_app(settings={
        "applications": ["guillotina.documentation"],
        "databases": {
            "db": {
                "storage": "DUMMY",
                "dsn": {},
                "name": "db"
            }
        },
        "root_user": {
            "password": "root"
        },
        "jwt": {
            "secret": "foobar",
            "algorithm": "HS256"
        },
    }, loop=loop)
    aioapp.config.execute_actions()
    load_cached_schema()

    server = TestServer(aioapp)
    loop.run_until_complete(server.start_server(loop=loop))
    _server = {
        'loop': loop,
        'server': server,
        'client': TestClient(server, loop=loop),
        'app': aioapp
    }
    return _server


def _clean_headers(headers):
    for key in list(headers.keys()):
        if key in IGNORED_HEADERS:
            del headers[key]
    return headers


class APICall(Directive):
    """
    Combines sphinxcontrib.httpdomain and sphinxcontrib.httpexample to
    interpret guillotina configuration and automatically generate documentation
    blocks for services
    """

    required_arguments = 0
    option_spec = {
        'method': directives.unchanged,
        'path': directives.unchanged,
        'path_spec': directives.unchanged,
        'headers': directives.unchanged,
        'basic_auth': directives.unchanged,
        'body': directives.unchanged,
        'disable-cache': directives.unchanged,
        'hidden': directives.unchanged,
    }

    async def handle_request(self, headers):
        server = get_server()
        client = server['client']
        method = (self.options.get('method') or 'get').lower()
        kwargs = {}
        if self.options.get('body'):
            kwargs['data'] = self.options['body']
        return await getattr(client, method)(
            self.options['path'], headers=headers, **kwargs)

    async def get_content(self, path):
        server = get_server()
        app = server['app']
        root = app.root

        request = get_mocked_request()
        path = path.split('?')[0]
        path = tuple(p for p in path.split('/') if p)
        ob, tail = await traverse(request, root, path)
        await abort(request)
        return ob, tail

    def get_service_definition(self, resource, tail):
        if tail and len(tail) > 0:
            # convert match lookups
            view_name = routes.path_to_view_name(tail)
        elif not tail:
            view_name = ''
        else:
            return None

        request = get_mocked_request()
        method = (self.options.get('method') or 'get').upper()
        method = app_settings['http_methods'][method]
        # container registry lookup
        try:
            view = query_multi_adapter(
                (resource, request), method, name=view_name)
            return view.__route__.service_configuration
        except AttributeError:
            pass

    def run(self):
        server = get_server()
        loop = server['loop']

        headers = {}
        for header in self.options.get('headers', '').split(','):
            if not header:
                continue
            name, value = header.split(':')
            headers[name.strip()] = value.strip()
        if 'Accept' not in headers:
            headers['Accept'] = 'application/json'

        if 'basic_auth' in self.options:
            encoded = b64encode(
                self.options['basic_auth'].encode('utf-8')).decode("ascii")
            headers['Authorization'] = 'Basic {}'.format(encoded)

        resp = loop.run_until_complete(self.handle_request(headers))
        if self.options.get('hidden'):
            return []
        path = self.options.get('path') or '/'
        ob, tail = loop.run_until_complete(self.get_content(path))
        service_definition = {}
        raw_service_definition = self.get_service_definition(ob, tail)
        if raw_service_definition is not None:
            for key, value in raw_service_definition.items():
                if key in ('method', 'permission', 'summary', 'description',
                           'responses', 'parameters'):
                    if callable(value):
                        value = value(ob)
                    service_definition[key] = value
            service_definition['context'] = get_dotted_name(
                raw_service_definition['context'])

        resp_body = None
        if resp.headers.get('content-type') == 'application/json':
            resp_body = loop.run_until_complete(resp.json())

        content = {
            'path_spec': self.options.get('path_spec'),
            'request': {
                'method': self.options.get('method', 'GET').upper(),
                'path': self.options.get('path') or '/',
                'headers': _clean_headers(headers),
                'body': self.options.get('body')
            },
            'response': {
                'status': resp.status,
                'headers': _clean_headers(dict(resp.headers)),
                'body': resp_body
            },
            'service': service_definition
        }
        content = json.dumps(content)

        content = content.replace(
            str(server['server'].make_url('')),
            '[server-url]')
        node = nodes.paragraph(
            content, content, classes=['g-api-call'])
        return [node]


def setup(app):
    app.add_directive_to_domain('http', 'gapi', APICall)
    dist = pkg_resources.get_distribution('guillotina')
    return {'version': dist.version}
