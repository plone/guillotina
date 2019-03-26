import json
import logging
from copy import deepcopy

from guillotina import testing
from guillotina import utils
from guillotina.component import globalregistry
from guillotina.factory import make_app


async def test_get_the_root(guillotina):
    response, status = await guillotina('GET', '/')
    assert response['static_directory'] == ['static', 'module_static', 'jsapp_static']
    assert 'db' in response['databases']
    assert 'db-custom' in response['databases']
    assert response['static_file'] == ['favicon.ico']


async def test_get_db(guillotina):
    response, status = await guillotina('GET', '/db')
    assert 'containers' in response


async def test_get_container(container_requester):
    async with container_requester as requester:
        response, status = await requester('GET', '/db/guillotina')
        assert response['@type'] == 'Container'


async def test_get_content(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina',
            data=json.dumps({
                '@type': 'Item',
                'id': 'hello',
                'title': 'Hola'
            }))
        assert status == 201
        response, status = await requester(
            'GET',
            '/db/guillotina/hello')
        assert status == 200


async def test_content_paths_are_correct(container_requester):
    async with container_requester as requester:
        response, status = await requester(
            'POST',
            '/db/guillotina',
            data=json.dumps({
                '@type': 'Item',
                'id': 'hello',
                'title': 'Hola'
            }))
        assert status == 201
        response, status = await requester(
            'GET',
            '/db/guillotina/hello')
        assert status == 200
        assert '/db/guillotina/hello' in response['@id']


def test_warn_about_jwt_secret(loop, caplog):
    settings = deepcopy(testing.get_settings())
    settings.update({
        'debug': False,
        'jwt': {
            "algorithm": "HS256",
            'secret': 'secret'
        }
    })
    with caplog.at_level(logging.WARNING, logger='guillotina'):
        globalregistry.reset()
        loop.run_until_complete(
            make_app(settings=settings, loop=loop))
        assert len(caplog.records) == 1
        assert 'strongly advised' in caplog.records[0].message


def test_warn_about_jwt_complexity(loop, caplog):
    settings = deepcopy(testing.get_settings())
    settings.update({
        'debug': False,
        'jwt': {
            "algorithm": "HS256",
            'secret': 'DKK@7328*!&@@'
        }
    })
    with caplog.at_level(logging.WARNING, logger='guillotina'):
        globalregistry.reset()
        loop.run_until_complete(
            make_app(settings=settings, loop=loop))
        assert len(caplog.records) == 1
        assert 'insecure secret' in caplog.records[0].message


def test_not_warn_about_jwt_secret(loop, caplog):
    settings = deepcopy(testing.get_settings())
    settings.update({
        'debug': True,
        'jwt': {
            "algorithm": "HS256",
            'secret': 'secret'
        }
    })
    with caplog.at_level(logging.WARNING, logger='guillotina'):
        globalregistry.reset()
        loop.run_until_complete(
            make_app(settings=settings, loop=loop))
        assert len(caplog.records) == 0


def test_warn_about_jwk_secret(loop, caplog):
    with caplog.at_level(logging.WARNING, logger='guillotina'):
        utils.get_jwk_key(settings={
            'debug': False
        })
        assert len(caplog.records) == 1
        assert 'has been dynamically generated' in caplog.records[0].message
