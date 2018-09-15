from guillotina.tests import fixtures
import asyncio
import json


settings = {
    'db_fixture': None,
    'guillotina_fixture': None,
    'requester_fixture': None,
    'requester': None
}


class Robot:

    def start_guillotina_server(self):
        loop = asyncio.get_event_loop()
        settings['guillotina_fixture'] = fixtures.guillotina_main(loop)
        settings['db_fixture'] = fixtures.db()
        settings['requester_fixture'] = fixtures.guillotina(
            next(settings['db_fixture']),
            next(settings['guillotina_fixture']),
            loop)
        settings['requester'] = next(settings['requester_fixture'])

    def stop_guillotina_server(self):
        next(settings['requester_fixture'])
        next(settings['guillotina_fixture'])
        next(settings['requester_fixture'])

    def get_guillotina_server_port(self):
        return settings['requester'].server.port

    def setup_guillotina_container(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            settings['requester']('POST', '/db/container'))

        _, status = loop.run_until_complete(
            settings['requester']('POST', '/db', data=json.dumps({
                "@type": "Container",
                "title": "Guillotina Container",
                "id": "container",
                "description": "Description Guillotina Container"
            })))
        if status != 200:
            print('Did not successfully create guillotina container')
