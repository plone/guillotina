# -*- encoding: utf-8 -*-
from guillotina.catalog.utils import get_index_fields
from guillotina.content import create_content
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import ICatalogUtility, ISecurityInfo
from guillotina.component import queryUtility, getAdapter
from guillotina.tests import utils as test_utils

import pytest


def test_indexed_fields(dummy_guillotina, loop):
    fields = get_index_fields('Item')
    assert 'type_name' in fields
    assert 'uuid' in fields
    assert 'path' in fields
    assert 'title' in fields
    assert 'creation_date' in fields


async def test_get_index_data(dummy_request):
    request = dummy_request  # noqa

    container = await create_content(
        'Container',
        id='guillotina',
        title='Guillotina')
    container.__name__ = 'guillotina'

    ob = await create_content('Item', id='foobar')

    data = ICatalogDataAdapter(ob)
    fields = await data()
    assert 'type_name' in fields
    assert 'uuid' in fields
    assert 'path' in fields
    assert 'title' in fields


async def test_registered_base_utility(dummy_request):
    util = queryUtility(ICatalogUtility)
    assert util is not None


async def test_get_security_data(dummy_request):
    request = dummy_request  # noqa
    ob = test_utils.create_content()
    adapter = getAdapter(ob, ISecurityInfo)
    data = adapter()
    assert 'access_users' in data
    assert 'access_roles' in data


async def test_get_data_uses_indexes_param(dummy_request):
    util = queryUtility(ICatalogUtility)
    request = dummy_request  # noqa
    container = await create_content(
        'Container',
        id='guillotina',
        title='Guillotina')
    container.__name__ = 'guillotina'
    ob = await create_content('Item', id='foobar')
    data = await util.get_data(ob, indexes=['title'])
    assert len(data) == 3  # uuid and type_name always returned

    data = await util.get_data(ob)
    assert len(data) > 7
