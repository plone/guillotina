# -*- coding: utf-8 -*-
from guillotina import schema
from guillotina.interfaces import IApplication
from guillotina.testing import GuillotinaFunctionalTestCase
from guillotina.tests import TEST_RESOURCES_DIR
from guillotina.tests import utils
from zope.component import getUtility
from zope.interface import Interface

import json
import os


class ITestingRegistry(Interface):
    enabled = schema.Bool(
        title="Example attribute")


async def test_get_root(site_requester):
    async for requester in site_requester:
        response, status = await requester('GET', '/')
        assert response['static_file'] == ['favicon.ico']
        assert response['databases'] == ['guillotina']
        assert response['static_directory'] == []


async def test_get_database(site_requester):
    """Get the database object."""
    async for requester in site_requester:
        response, status = await requester('GET', '/guillotina')
        len(response['sites']) == 1


async def test_get_guillotina(site_requester):
    """Get the root guillotina site."""
    async for requester in site_requester:
        response, status = await requester('GET', '/guillotina/guillotina')
        assert len(response['items']) == 0


async def test_get_contenttypes(site_requester):
    """Check list of content types."""
    async for requester in site_requester:
        response, status = await requester('GET', '/guillotina/guillotina/@types')
        assert status == 200
        assert len(response) > 1
        assert any("Item" in s['title'] for s in response)
        assert any("Site" in s['title'] for s in response)


async def test_get_contenttype(site_requester):
    """Get a content type definition."""
    async for requester in site_requester:
        response, status = await requester('GET', '/guillotina/guillotina/@types/Item')
        assert status == 200
        assert len(response['definitions']) == 1
        assert response['title'] == 'Item'


async def test_get_registries(site_requester):
    """Get the list of registries."""
    async for requester in site_requester:
        response, status = await requester('GET', '/guillotina/guillotina/@registry')
        assert status == 200
        assert len(response['value']) == 2
        assert 'guillotina.interfaces.registry.ILayers.active_layers' in response['value']


async def test_get_registry_value(site_requester):
    """Check a value from registry."""
    async for requester in site_requester:
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/@registry/guillotina.interfaces.registry.ILayers.active_layers')
        assert response['value'] == ['guillotina.interfaces.layer.IDefaultLayer']


async def test_create_contenttype(site_requester):
    async for requester in site_requester:
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
        request = utils.get_mocked_request(requester.db)
        root = await utils.get_root(request)
        site = await root.__getitem__('guillotina')
        obj = await site.__getitem__('item1')
        assert obj.title == 'Item1'


async def test_create_delete_contenttype(site_requester):
    """Create and delete a content type."""
    async for requester in site_requester:
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
        response, status = await requester('DELETE', '/guillotina/guillotina/item1')
        assert status == 200


async def test_register_registry(site_requester):
    async for requester in site_requester:
        response, status = await requester(
            'POST',
            '/guillotina/guillotina/@registry',
            data=json.dumps({
                "interface": "guillotina.tests.test_api.ITestingRegistry",
                "initial_values": {
                    "enabled": True
                }
            })
        )
        assert status == 201

        response, status = await requester(
            'PATCH',
            '/guillotina/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled',
            data=json.dumps({
                "value": False
            })
        )
        assert status == 204
        response, status = await requester(
            'GET',
            '/guillotina/guillotina/@registry/guillotina.tests.test_api.ITestingRegistry.enabled')
        assert {'value': False} == response


# class FunctionalTestServer(GuillotinaFunctionalTestCase):
#     """Functional testing of the API REST."""
#
#     def _get_site(self):
#         """
#         sometimes the site does not get updated data from zodb
#         this seems to make it
#         """
#         return self.new_root()['guillotina']
#
#     # def test_file_upload(self):
#     #     resp = self.layer.requester(
#     #         'POST',
#     #         '/guillotina/guillotina/',
#     #         data=json.dumps({
#     #             "@type": "File",
#     #             "title": "File1",
#     #             "id": "file1"
#     #         })
#     #     )
#     #     self.assertTrue(resp.status_code == 201)
#     #     site = self._get_site()
#     #     self.assertTrue('file1' in site)
#     #     fi = open(os.path.join(TEST_RESOURCES_DIR, 'plone.png'), 'rb')
#     #     data = fi.read()
#     #     fi.close()
#     #     resp = self.layer.requester(
#     #         'PATCH',
#     #         '/guillotina/guillotina/file1/@upload/file',
#     #         data=data)
#     #     site = self._get_site()
#     #     behavior = IAttachment(site['file1'])
#     #     self.assertEqual(behavior.file.data, data)
#
#     # def test_file_download(self):
#     #     # first, get a file on...
#     #     self.test_file_upload()
#     #     resp = self.layer.requester(
#     #         'GET',
#     #         '/guillotina/guillotina/file1/@download/file')
#     #     site = self._get_site()
#     #     behavior = IAttachment(site['file1'])
#     #     self.assertEqual(behavior.file.data, resp.content)
#
#     def test_create_contenttype_with_date(self):
#         """Try to create a contenttype."""
#         resp = self.layer.requester(
#             'POST',
#             '/guillotina/guillotina/',
#             data=json.dumps({
#                 "@type": "Item",
#                 "title": "Item1",
#                 "id": "item1",
#             })
#         )
#         self.assertTrue(resp.status_code == 201)
#         date_to_test = "2016-11-30T14:39:07.394273+01:00"
#         resp = self.layer.requester(
#             'PATCH',
#             '/guillotina/guillotina/item1',
#             data=json.dumps({
#                 "guillotina.behaviors.dublincore.IDublinCore": {
#                     "created": date_to_test,
#                     "expires": date_to_test
#                 }
#             })
#         )
#
#         root = self.new_root()
#         obj = root['guillotina']['item1']
#         from guillotina.behaviors.dublincore import IDublinCore
#         self.assertEqual(IDublinCore(obj).created.isoformat(), date_to_test)
#         self.assertEqual(IDublinCore(obj).expires.isoformat(), date_to_test)
#
#     def test_create_duplicate_id(self):
#         """Try to create a contenttype."""
#         resp = self.layer.requester(
#             'POST',
#             '/guillotina/guillotina/',
#             data=json.dumps({
#                 "@type": "Item",
#                 "title": "Item1",
#                 "id": "item1",
#             })
#         )
#         self.assertTrue(resp.status_code == 201)
#         resp = self.layer.requester(
#             'POST',
#             '/guillotina/guillotina/',
#             data=json.dumps({
#                 "@type": "Item",
#                 "title": "Item1",
#                 "id": "item1",
#             })
#         )
#         self.assertTrue(resp.status_code == 409)
#         resp = self.layer.requester(
#             'POST',
#             '/guillotina/guillotina/',
#             data=json.dumps({
#                 "@type": "Item",
#                 "title": "Item1",
#                 "id": "item1",
#             }),
#             headers={
#                 "OVERWRITE": "TRUE"
#             }
#         )
#         self.assertTrue(resp.status_code == 201)
#
#     def test_create_nested_object(self):
#         resp = self.layer.requester(
#             'POST',
#             '/guillotina/guillotina/',
#             data=json.dumps({
#                 '@type': 'Example',
#                 'title': 'Item1',
#                 'id': 'item1',
#                 'categories': [{
#                     'label': 'term1',
#                     'number': 1.0
#                 }, {
#                     'label': 'term2',
#                     'number': 2.0
#                 }]
#             })
#         )
#         self.assertTrue(resp.status_code == 201)
#
#     def test_get_addons(self):
#         resp = self.layer.requester(
#             'GET', '/guillotina/guillotina/@addons'
#         )
#         self.assertEqual(resp.status_code, 200)
