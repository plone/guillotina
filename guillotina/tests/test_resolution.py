from guillotina import configure
from guillotina.annotations import AnnotationData
from guillotina.api.content import DefaultPATCH
from guillotina.behaviors.dublincore import IDublinCore
from guillotina.component import queryMultiAdapter
from guillotina.db.interfaces import IWriter
from guillotina.db.resolution import get_change_key
from guillotina.db.resolution import record_object_change
from guillotina.db.transaction import Transaction
from guillotina.exceptions import UnresolvableConflict
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceDeserializeFromJson
from guillotina.tests import mocks
from guillotina.tests.utils import create_content
from guillotina.tests.utils import get_mocked_request

import asyncio
import json
import pytest


def test_record_change_adds_to_object():
    ob = create_content()
    record_object_change(ob, IResource['title'], 'foobar')
    key = get_change_key(IResource['title'])
    assert key in ob.__changes__
    assert ob.__changes__[key]['value'] == 'foobar'


def test_record_again_does_not_overwrite_but_keeps_original():
    ob = create_content()
    record_object_change(ob, IResource['title'], 'foobar')
    record_object_change(ob, IResource['title'], 'foobar2')
    key = get_change_key(IResource['title'])
    assert key in ob.__changes__
    assert ob.__changes__[key]['value'] == 'foobar'


async def test_serializer_adds_to_changes(dummy_guillotina):
    ob = create_content()
    trns = Transaction(mocks.MockManager())
    ob._p_jar = trns
    ob.title = 'foobar'
    deserializer = queryMultiAdapter((ob, get_mocked_request()),
                                     IResourceDeserializeFromJson)
    await deserializer({
        'title': 'foobar new'
    }, ignore_errors=True)
    key = get_change_key(IResource['title'])
    assert key in ob.__changes__
    assert ob.__changes__[key]['value'] == 'foobar'
    assert ob.title == 'foobar new'


async def test_cannot_resolve_conflict(dummy_guillotina):
    # dummy_guillotina setups up adapters/utilities for us
    trns = Transaction(mocks.MockManager())
    ob = create_content()
    writer = IWriter(ob)

    ob.title = 'foobar-other'
    # get state now so it has the 'foobar-other' value...
    state = writer.serialize()

    ob.title = 'foobar-this'

    # should conflict because we're assuming a different title start value of 'foobar-diff'
    # so we don't have a proper starting point to compare diff of obs against
    record_object_change(ob, IResource['title'], 'foobar-diff')

    ob._p_oid = 'foobar'
    trns.modified['foobar'] = ob

    with pytest.raises(UnresolvableConflict):
        await trns.resolve_conflict({
            'zoid': 'foobar',
            'state': state,
            'tid': 1,
            'id': 'foobar'
        })


async def test_resolve_conflict(dummy_guillotina):
    # dummy_guillotina setups up adapters/utilities for us
    trns = Transaction(mocks.MockManager())
    ob = create_content()
    writer = IWriter(ob)

    ob.title = 'foobar-other'
    # get state from
    state = writer.serialize()
    # should not conflict because it's a diff attribute
    ob.description = 'foobar-desc'
    record_object_change(ob, IDublinCore['description'], 'foobar-other')

    ob._p_oid = 'foobar'
    trns.modified['foobar'] = ob

    new_obj = await trns.resolve_conflict({
        'zoid': 'foobar',
        'state': state,
        'tid': 1,
        'id': 'foobar'
    })

    assert new_obj.title == 'foobar-other'
    assert new_obj.description == 'foobar-desc'


async def test_cannot_resolve_annotation_conflict(dummy_guillotina):
    # dummy_guillotina setups up adapters/utilities for us
    trns = Transaction(mocks.MockManager())
    ob = AnnotationData()

    writer = IWriter(ob)

    ob['title'] = 'foobar-other'
    # get state now so it has the 'foobar-other' value...
    state = writer.serialize()

    ob['title'] = 'foobar-this'

    # should conflict because we're assuming a different title start value of 'foobar-diff'
    # so we don't have a proper starting point to compare diff of obs against
    record_object_change(ob, field=IResource['title'], key='title', value='foobar-diff')

    ob._p_oid = 'foobar'
    trns.modified['foobar'] = ob

    with pytest.raises(UnresolvableConflict):
        await trns.resolve_conflict({
            'zoid': 'foobar',
            'state': state,
            'tid': 1,
            'id': 'foobar'
        })


async def test_resolve_annotaion_conflict(dummy_guillotina):
    # dummy_guillotina setups up adapters/utilities for us
    trns = Transaction(mocks.MockManager())
    ob = AnnotationData()
    writer = IWriter(ob)

    ob['title'] = 'foobar-other'
    # get state from
    state = writer.serialize()
    # should not conflict because it's a diff attribute
    ob['description'] = 'foobar-desc'
    record_object_change(ob, field=IDublinCore['description'],
                         key='description', value='foobar-other')

    ob._p_oid = 'foobar'
    trns.modified['foobar'] = ob

    new_obj = await trns.resolve_conflict({
        'zoid': 'foobar',
        'state': state,
        'tid': 1,
        'id': 'foobar'
    })

    assert new_obj['title'] == 'foobar-other'
    assert new_obj['description'] == 'foobar-desc'


async def test_retry_request_on_conflict(container_requester):

    class SlowPatchService(DefaultPATCH):
        async def __call__(self):
            await asyncio.sleep(0.5)
            return await super().__call__()

    configure.register_configuration(SlowPatchService, dict(
        context=IResource,
        name="@slowpatch",
        method='PATCH',
        permission='guillotina.ModifyContent'
    ), 'service')

    async with await container_requester as requester:
        config = requester.root.app.config
        configure.load_configuration(
            config, 'guillotina.tests', 'service')
        config.execute_actions()

        response, status = await requester('POST', '/db/guillotina', data=json.dumps({
            'id': 'foobar',
            'title': 'foobar',
            '@type': 'Item'
        }))

        async def delayed_patch():
            # ensure the slow patch was started before the regular one
            await asyncio.sleep(0.1)
            await requester.make_request('PATCH', '/db/guillotina/foobar', data=json.dumps({
                'title': 'fastvalue'
            }))

        results = await asyncio.gather(
            requester.make_request('PATCH', '/db/guillotina/foobar/@slowpatch', data=json.dumps({
                'title': 'slowvalue'
            })),
            delayed_patch()
        )
        assert results[0][2]['X-Retry-Transaction-Count'] == '1'

        response, status = await requester('GET', '/db/guillotina/foobar')
        assert response['title'] == 'slowvalue'
