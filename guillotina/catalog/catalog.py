# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import queryAdapter
from guillotina.content import iter_schemata_for_type
from guillotina.directives import index
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import merged_tagged_value_list
from guillotina.directives import metadata
from guillotina.exceptions import NoIndexField
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces import ISecurityInfo
from guillotina.json.serialize_value import json_compatible
from guillotina.security.security_code import principal_permission_manager
from guillotina.security.security_code import role_permission_manager
from guillotina.security.utils import get_principals_with_access_content
from guillotina.security.utils import get_roles_with_access_content
from zope.interface import implementer


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

    async def get_by_path(self, container, path, depth=-1, query={}, doc_type=None):
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

    async def reindex_all_content(self, container):
        """ For all Dexterity Content add a queue task that reindex the object
        """
        pass

    async def initialize_catalog(self, container):
        """ Creates an index
        """
        pass

    async def remove_catalog(self, container):
        """ Deletes an index
        """
        pass

    async def get_data(self, content):
        data = {}
        adapter = queryAdapter(content, ICatalogDataAdapter)
        if adapter:
            data.update(await adapter())
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
            'type_name': self.content.type_name
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

        value = getattr(ob, field_name, None)
        return json_compatible(value)

    async def __call__(self):
        # For each type
        values = {}

        for schema in iter_schemata_for_type(self.content.type_name):
            behavior = schema(self.content)
            if IAsyncBehavior.implementedBy(behavior.__class__):
                # providedBy not working here?
                await behavior.load(create=False)
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
