# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.catalog import NoIndexField
from plone.server.content import iter_schemata_for_type
from plone.server.directives import index
from plone.server.directives import merged_tagged_value_dict
from plone.server.directives import merged_tagged_value_list
from plone.server.directives import metadata
from plone.server.interfaces import ICatalogDataAdapter
from plone.server.interfaces import ICatalogUtility
from plone.server.interfaces import IResource
from plone.server.json.serialize_value import json_compatible
from zope.component import queryAdapter
from zope.interface import implementer
from plone.server.auth import principal_permission_manager
from plone.server.auth import role_permission_manager
from plone.server.auth import get_principals_with_access_content
from plone.server.auth import get_roles_with_access_content
from plone.server.interfaces import ISecurityInfo


global_principal_permission_setting = principal_permission_manager.get_setting
global_roles_for_permission = role_permission_manager.get_roles_for_permission


@implementer(ICatalogUtility)
class DefaultSearchUtility(object):

    async def search(self, query):
        pass

    async def get_by_uuid(self, uuid):
        pass

    async def get_object_by_uuid(self, uuid):
        pass

    async def get_by_type(self, doc_type, query={}):
        pass

    async def get_by_path(self, site, path, depth=-1, query={}, doc_type=None):
        pass

    async def get_folder_contents(self, obj):
        pass

    async def index(self, datas):
        """
        {uid: <dict>}
        """
        pass

    async def remove(self, uids):
        """
        list of UIDs to remove from index
        """
        pass

    async def reindex_all_content(self):
        """ For all Dexterity Content add a queue task that reindex the object
        """
        pass

    async def initialize_catalog(self):
        """ Creates an index
        """
        pass

    async def remove_catalog(self):
        """ Deletes an index
        """
        pass

    def get_data(self, content):
        data = {}
        adapter = queryAdapter(content, ICatalogDataAdapter)
        if adapter:
            data.update(adapter())
        return data


@configure.adapter(
    for_=IResource,
    provides=ISecurityInfo)
class DefaultSecurityInfoAdapter(object):
    def __init__(self, content):
        self.content = content

    def __call__(self):
        """ access_users and access_roles """
        return {
            'access_users': get_principals_with_access_content(self.content),
            'access_roles': get_roles_with_access_content(self.content),
            'portal_type': self.content.portal_type
        }


@configure.adapter(
    for_=IResource,
    provides=ICatalogDataAdapter)
class DefaultCatalogDataAdapter(object):

    def __init__(self, content):
        self.content = content

    def get_data(self, ob, iface, field_name):
        try:
            field = iface[field_name]
            real_field = field.bind(ob)
            try:
                value = real_field.get(ob)
                return json_compatible(value)
            except AttributeError:
                pass
        except KeyError:
            pass

        return json_compatible(getattr(ob, field_name, None))

    def __call__(self):
        # For each type
        values = {}

        for schema in iter_schemata_for_type(self.content.portal_type):
            behavior = schema(self.content)
            for index_name, index_data in merged_tagged_value_dict(schema, index.key).items():
                try:
                    if 'accessor' in index_data:
                        values[index_name] = index_data['accessor'](behavior)
                    else:
                        values[index_name] = self.get_data(behavior, schema, index_name)
                except NoIndexField:
                    pass
            for metadata_name in merged_tagged_value_list(schema, metadata.key):
                values[metadata_name] = self.get_data(behavior, schema, metadata_name)

        return values
