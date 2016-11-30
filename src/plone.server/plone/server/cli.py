# -*- coding: utf-8 -*-
from aiohttp import web
import plone.server.patch  # noqa
from plone.server.factory import make_app
from plone.server import app_settings
from plone.server.testing import TESTING_SETTINGS, PloneRequester

import argparse
import logging
import threading
import asyncio
import time
from pprint import pformat


logger = logging.getLogger('plone.server')


def format_headers(headers):
    return '\n'.join(['\t{}: {}'.format(n, v)
                      for n, v in headers.items()])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--method', nargs='?',
                        default='get', help='HTTP method')
    parser.add_argument('-p', '--path', nargs='?',
                        default='/', help='Path to endpoint')
    parser.add_argument('-b', '--body', default=u'',
                        help='Request body')
    parser.add_argument('-c', '--configuration',
                        default='config.json', help='Configuration file')
    arguments = parser.parse_args()

    aioapp = make_app(config_file=arguments.configuration)
    app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']

    loop = aioapp.loop
    handler = aioapp.make_handler(keep_alive_on=False)
    loop.run_until_complete(loop.create_server(
        handler,
        '127.0.0.1',
        5777))

    def loop_in_thread(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    t = threading.Thread(target=loop_in_thread, args=(loop,))
    t.start()

    req_body = arguments.body or ''

    requester = PloneRequester('http://localhost:5777')
    resp = requester(
        arguments.method, arguments.path,
        data=req_body or None)

    print('''
Path: {path}
Method: {method}
Status code: {code}
Request Headers:
{request_headers}

Response Headers:
{response_headers}

Request body:
{request_body}

Response body:
{body}
'''.format(
        path=arguments.path,
        method=arguments.method,
        code=resp.status_code,
        request_headers=format_headers(resp.request.headers),
        response_headers=format_headers(resp.headers),
        body=pformat(resp.json()),
        request_body=req_body
    ))

    loop.call_soon_threadsafe(loop.stop)
    while(loop.is_running()):
        time.sleep(1)


if __name__ == '__main__':
    main()
