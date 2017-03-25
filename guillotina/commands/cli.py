from guillotina import app_settings
from guillotina.commands import Command
from guillotina.testing import GuillotinaRequester
from guillotina.testing import TESTING_SETTINGS
from pprint import pformat

import asyncio
import threading
import time


def format_headers(headers):
    return '\n'.join(['\t{}: {}'.format(n, v)
                      for n, v in headers.items()])


class CliCommand(Command):
    description = 'Guillotina server CLI utility'

    def get_parser(self):
        parser = super(CliCommand, self).get_parser()
        parser.add_argument('-m', '--method', nargs='?',
                            default='get', help='HTTP method')
        parser.add_argument('-p', '--path', nargs='?',
                            default='/', help='Path to endpoint')
        parser.add_argument('-b', '--body', default=u'',
                            help='Request body')
        return parser

    async def run(self, arguments, settings, app):
        app_settings['root_user']['password'] = TESTING_SETTINGS['root_user']['password']

        loop = app.loop
        handler = app.make_handler(keep_alive_on=False)
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

        requester = GuillotinaRequester('http://localhost:5777')
        resp = await requester(
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
