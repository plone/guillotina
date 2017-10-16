# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import queryAdapter
from guillotina.content import iter_schemata
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
from guillotina.utils import get_content_depth
from guillotina.utils import get_content_path
from zope.interface import implementer


global_principal_permission_setting = principal_permission_manager.get_setting
global_roles_for_permission = role_permission_manager.get_roles_for_permission


@implementer(ICatalogUtility)
class DefaultSearchUtility(object):

    async def initialize(self, app):
        pass

    async def search(self, container, query):
        pass

    async def get_by_uuid(self, container, uuid):
        pass

    async def get_object_by_uuid(self, container, uuid):
        pass

    async def get_by_type(self, container, doc_type, query={}):
        pass

    async def get_by_path(self, container, path, depth=-1, query={}, doc_type=None):
        pass

    async def get_folder_contents(self, container, parent_uid):
        pass

    async def index(self, container, datas):
        """
        {uid: <dict>}
        """
        pass

    async def update(self, container, datas):
        """
        {uid: <dict>}
        """
        pass

    async def remove(self, container, uids):
        """
        list of UIDs to remove from index
        """
        pass

    async def reindex_all_content(self, container, security=False):
        """ For all content add a queue task that reindex the object
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

    async def get_data(self, content, indexes=None):
        data = {}
        adapter = queryAdapter(content, ICatalogDataAdapter)
        if adapter:
            data.update(await adapter(indexes))
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
            'path': get_content_path(self.content),
            'depth': get_content_depth(self.content),
            'parent_uuid': getattr(
                getattr(self.content, '__parent__', None), 'uuid', None),
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

    async def load_behavior(self, behavior):
        if IAsyncBehavior.implementedBy(behavior.__class__):
            # providedBy not working here?
            await behavior.load(create=False)

    async def __call__(self, indexes=None):
        # For each type
        values = {
            'type_name': self.content.type_name
        }

        for schema in iter_schemata(self.content):
            behavior = schema(self.content)
            loaded = False
            for index_name, index_data in merged_tagged_value_dict(schema, index.key).items():
                if index_name in values:
                    # you can override indexers so we do not want to index
                    # the same value more than once
                    continue

                try:
                    # accessors we always reindex since we can't know if updated
                    # from the indexes param--they are "fake" like indexes, not fields
                    if ('accessor' in index_data and (
                            indexes is None or index_data.get('field') in indexes)):
                        if not loaded:
                            await self.load_behavior(behavior)
                            loaded = True
                        values[index_name] = index_data['accessor'](behavior)
                    elif (indexes is None or index_name in indexes or
                            isinstance(getattr(type(self.content), index_name, None), property)):
                        if not loaded:
                            await self.load_behavior(behavior)
                            loaded = True
                        # in this case, properties are also dynamic so we have to make sure
                        # to allow for them to be reindexed every time.
                        values[index_name] = self.get_data(behavior, schema, index_name)
                except NoIndexField:
                    pass

            for metadata_name in merged_tagged_value_list(schema, metadata.key):
                if (indexes is not None and metadata_name not in indexes and
                        not isinstance(getattr(type(self.content), metadata_name, None), property)):
                    # in this case, properties are also dynamic so we have to make sure
                    # to allow for them to be reindexed every time.
                    continue  # skip
                if not loaded:
                    await self.load_behavior(behavior)
                    loaded = True
                try:
                    values[metadata_name] = self.get_data(behavior, schema, metadata_name)
                except NoIndexField:
                    pass
        return values
