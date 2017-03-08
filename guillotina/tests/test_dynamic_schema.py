# -*- coding: utf-8 -*-
from guillotina.tests import TEST_RESOURCES_DIR

import json
import os


async def test_set_dynamic_behavior(site_requester):
    async with await site_requester as requester:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        assert status == 201

        # We create the behavior
        response, status = await requester(
            'PATCH',
            '/guillotina/guillotina/item1/@behaviors',
            data=json.dumps({
                'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
            })
        )
        assert status == 200

        # We check that the behavior is there
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/item1'
        )

        assert response['__behaviors__'] == ['guillotina.behaviors.dublincore.IDublinCore']
        assert 'guillotina.behaviors.dublincore.IDublinCore' in response

    # def test_create_delete_dynamic_behavior(self):
    #     """Create and delete a content type."""
    #     resp = self.layer.requester(
    #         'POST',
    #         '/guillotina/guillotina/',
    #         data=json.dumps({
    #             "@type": "Item",
    #             "title": "Item1",
    #             "id": "item1"
    #         })
    #     )
    #     self.assertTrue(resp.status_code == 201)
    #
    #     # We create the behavior
    #     resp = self.layer.requester(
    #         'PATCH',
    #         '/guillotina/guillotina/item1/@behaviors',
    #         data=json.dumps({
    #             'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
    #         })
    #     )
    #     self.assertTrue(resp.status_code == 200)
    #
    #     # We check that the behavior is there
    #     resp = self.layer.requester(
    #         'GET',
    #         '/guillotina/guillotina/item1'
    #     )
    #
    #     self.assertEqual(
    #         resp.json()['__behaviors__'],
    #         ['guillotina.behaviors.dublincore.IDublinCore'])
    #
    #     # We delete the behavior
    #     resp = self.layer.requester(
    #         'DELETE',
    #         '/guillotina/guillotina/item1/@behaviors',
    #         data=json.dumps({
    #             'behavior': 'guillotina.behaviors.dublincore.IDublinCore'
    #         })
    #     )
    #     self.assertTrue(resp.status_code == 200)
    #
    #     # We check that the behavior is there
    #     resp = self.layer.requester(
    #         'GET',
    #         '/guillotina/guillotina/item1'
    #     )
    #
    #     self.assertEqual(
    #         resp.json()['__behaviors__'],
    #         [])
    #
    #     self.assertTrue(
    #         'guillotina.behaviors.dublincore.IDublinCore' not in
    #         resp.json())
    #
    # def test_get_behaviors(self):
    #     """Try to create a contenttype."""
    #     resp = self.layer.requester(
    #         'POST',
    #         '/guillotina/guillotina/',
    #         data=json.dumps({
    #             "@type": "Item",
    #             "title": "Item1",
    #             "id": "item1"
    #         })
    #     )
    #     self.assertTrue(resp.status_code == 201)
    #
    #     resp = self.layer.requester(
    #         'GET',
    #         '/guillotina/guillotina/item1/@behaviors'
    #     )
    #
    #     self.assertTrue(resp.status_code == 200)
    #     self.assertTrue(
    #         'guillotina.behaviors.dublincore.IDublinCore' in resp.json()['available'])  # noqa
    #     self.assertTrue(
    #         'guillotina.behaviors.dublincore.IDublinCore' in resp.json())
