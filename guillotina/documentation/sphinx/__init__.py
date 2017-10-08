# -*- coding: utf-8 -*-
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.directives import CodeBlock
from sphinxcontrib.httpexample import utils as httpex_utils
from sphinxcontrib.httpexample.directives import HTTPExample

import json
import os
import pkg_resources
import tempfile


method_sort_order = [
    'get',
    'post',
    'patch',
    'delete',
    'options'
]


def service_filename_sort_key(filename):
    name = filename.split('.')[0]
    parts = name.split('-')
    if len(parts) == 2:
        # no @ service on it...
        return '0-{}'.format(method_sort_order.index(parts[1]))
    else:
        return '1-{}-{}'.format(
            parts[2],
            method_sort_order.index(parts[1]))


class HTTPService(CodeBlock):
    """
    Combines sphinxcontrib.httpdomain and sphinxcontrib.httpexample to
    interpret guillotina configuration and automatically generate documentation
    blocks for services
    """

    required_arguments = 0
    option_spec = httpex_utils.merge_dicts(CodeBlock.option_spec, {
        'type': directives.unchanged,
        'directory': directives.unchanged
    })

    def __init__(self, *args, **kwargs):
        super(HTTPService, self).__init__(*args, **kwargs)
        cwd = os.path.dirname(self.state.document.current_source)
        self.dir = os.path.normpath(os.path.join(cwd, self.options['directory']))

    def get_json_from_file(self, filename):
        fi = open(filename, 'r')
        data = json.loads(fi.read())
        fi.close()
        return data

    def write_tmp(self, data):
        _, filename = tempfile.mkstemp()
        fi = open(filename, 'w')
        fi.write(data)
        fi.close()
        return filename

    def process_service(self, filename):
        data = self.get_json_from_file(os.path.join(self.dir, filename))
        request_filename = self.write_tmp(data['request'] or '')
        response_filename = self.write_tmp(data['response'] or '')

        example = HTTPExample(
            'http:example',
            arguments=['curl', 'httpie', 'python-requests'],
            options={
                'request': request_filename,
                'response': response_filename
            },
            content=self.content,
            lineno=self.lineno,
            content_offset=self.content_offset,
            block_text='.. http:example::',
            state=self.state,
            state_machine=self.state_machine
        )

        method = data['method'].upper()
        service = data['service']
        name = service.get('name') or ''
        path_scheme = data.get('path_scheme') or name
        summary = service.get('summary') or ''
        permission = service.get('permission') or ''

        container = nodes.container('')
        container.append(addnodes.desc_name('', method + ' '))
        container.append(addnodes.desc_name('', path_scheme))

        inner_container = nodes.definition('')
        container.append(inner_container)

        inner_container.append(nodes.paragraph(summary, summary))
        inner_container.append(addnodes.desc_name('permission', 'permission'))
        perm_label = ': ' + permission
        inner_container.append(addnodes.desc_annotation(perm_label, perm_label))
        inner_container.append(example.run()[0])

        # extra = nodes.paragraph('', '')
        # inner_container.append(extra)
        # if service.get('responses'):
        #     extra.append(nodes.strong('', 'Responses'))
        #     blist = nodes.bullet_list('')
        #     extra.append(blist)
        #     for code, config in service['responses'].items():
        #         blist.append(render_response(code, 'Hello'))

        # cleanup
        os.remove(request_filename)
        os.remove(response_filename)

        return container

    def run(self):
        type_name = self.options['type']
        files = []
        for filename in os.listdir(self.dir):
            if filename.startswith(type_name + '-'):
                files.append(filename)
        files.sort(key=service_filename_sort_key)

        env = self.state.document.settings.env
        targetid = "service-%d" % env.new_serialno('service')
        targetnode = nodes.target('', '', ids=[targetid])

        return [targetnode] + [self.process_service(filename) for filename in files]


def setup(app):
    app.add_directive_to_domain('http', 'service', HTTPService)
    dist = pkg_resources.get_distribution('guillotina')
    return {'version': dist.version}
