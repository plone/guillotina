# -*- coding: utf-8 -*-
from aiohttp.test_utils import TestClient
from aiohttp.test_utils import TestServer
from base64 import b64encode
from docutils import nodes
from docutils.parsers.rst import Directive  # type: ignore
from docutils.parsers.rst import directives  # type: ignore
from guillotina import routes
from guillotina._settings import app_settings
from guillotina.component import query_multi_adapter
from guillotina.content import load_cached_schema
from guillotina.factory import make_app
from guillotina.tests.utils import get_mocked_request
from guillotina.transactions import abort
from guillotina.traversal import traverse
from guillotina.utils import get_dotted_name
from zope.interface import Interface

import asyncio
import docutils.statemachine
import json
import pkg_resources

_server = None

IGNORED_HEADERS = ('Accept-Encoding', 'Connection', 'User-Agent', 'Date',
                   'Access-Control-Allow-Credentials',
                   'Access-Control-Expose-Headers', 'Server')


def get_server():
    global _server
    if _server is not None:
        return _server

    loop = asyncio.new_event_loop()
    aioapp = make_app(
        settings={
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
        },
        loop=loop)
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


def _fmt_body(body, indent):
    if body is None:
        return ""
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except Exception:
            return body
    body = json.dumps(body, indent=4)
    body = ('\n' + ' ' * indent).join(body.split('\n'))
    return body


def _fmt_headers(headers, indent):
    return ('\n' + ' ' * indent).join(
        '%s: %s' % (name, headers[name]) for name in sorted(headers))


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

        path = self.options.get('path') or '/'
        ob, tail = loop.run_until_complete(self.get_content(path))

        resp = loop.run_until_complete(self.handle_request(headers))
        if 'hidden' in self.options:
            return []

        service_definition = {}
        service_definition.setdefault('description', '')
        service_definition.setdefault('summary', '')
        service_definition.setdefault('permission', '')
        service_definition.setdefault('context', '')

        raw_service_definition = self.get_service_definition(ob, tail)
        if raw_service_definition is not None:
            for key, value in raw_service_definition.items():
                if key in ('method', 'permission', 'summary', 'description',
                           'responses', 'parameters'):
                    if callable(value):
                        value = value(ob)
                    service_definition[key] = value
            service_definition['context'] = get_dotted_name(
                raw_service_definition.get('context', Interface))

        resp_body = None
        if resp.headers.get('content-type') == 'application/json':
            resp_body = loop.run_until_complete(resp.json())
            resp_body = _fmt_body(resp_body, 8)
        else:
            resp_body = loop.run_until_complete(resp.text())

        content = {
            'path_spec': (self.options.get('path_spec') or
                          self.options.get('method', 'GET').upper()),
            'request': {
                'method': self.options.get('method', 'GET').upper(),
                'method_lower': self.options.get('method', 'GET').lower(),
                'path': self.options.get('path') or '/',
                'headers': _fmt_headers(_clean_headers(headers), 8),
                'body': _fmt_body(self.options.get('body'), 8)
            },
            'response': {
                'status': resp.status,
                'headers': _fmt_headers(_clean_headers(dict(resp.headers)), 8),
                'body': resp_body
            },
            'service':
            service_definition,
        }
        rst_content = """.. http:{request[method_lower]}:: {path_spec}

    {service[summary]}

    {service[description]}

    - Permission: **{service[permission]}**
    - Context: **{service[context]}**

    .. http:example:: curl httpie

        {request[method]} {request[path]} HTTP/1.1
        {request[headers]}

        {request[body]}


        HTTP/1.1 {response[status]} OK
        {response[headers]}

        {response[body]}

"""
        rst_content = rst_content.format(**content)

        for parameter in service_definition.get('parameters', []):
            if isinstance(parameter, str):
                parameter = {'name': parameter, 'type': 'string'}
            if parameter.get('in', 'query') != 'query':
                continue
            parameter.setdefault('description', '')
            if parameter.get('required'):
                parameter['description'] += ' (required)'
            elif parameter.get('default'):
                parameter['description'] += ' (default: {default})'.format(
                    **parameter)
            rst_content += '\n    :query {type} {name}: {description}'.format(
                **parameter)

        responses = {
            code: info['description']
            for code, info in service_definition.get('responses', {}).items()
        }
        responses.setdefault('401',
                             'You are not authorized to perform the operation')
        responses.setdefault('404', 'The resource does not exist')
        for code in sorted(responses):
            rst_content += ('\n    :statuscode {}: {}'.format(
                code, responses[code]))
        rst_content = rst_content.split("\n")
        view = docutils.statemachine.StringList(rst_content, '<gapi>')

        node = nodes.paragraph()
        self.state.nested_parse(view, 0, node)
        return [node]


def setup(app):
    app.add_directive_to_domain('http', 'gapi', APICall)
    dist = pkg_resources.get_distribution('guillotina')
    return {'version': dist.version}
