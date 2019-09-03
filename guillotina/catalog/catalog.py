from guillotina import configure
from guillotina.catalog.utils import parse_query
from guillotina.component import query_adapter
from guillotina.content import iter_schemata
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.directives import index
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import merged_tagged_value_list
from guillotina.directives import metadata
from guillotina.exceptions import ContainerNotFound
from guillotina.exceptions import NoIndexField
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import ICatalogDataAdapter
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IContainer
from guillotina.interfaces import IResource
from guillotina.interfaces import ISecurityInfo
from guillotina.json.serialize_value import json_compatible
from guillotina.security.security_code import principal_permission_manager
from guillotina.security.security_code import role_permission_manager
from guillotina.security.utils import get_principals_with_access_content
from guillotina.security.utils import get_roles_with_access_content
from guillotina.utils import apply_coroutine
from guillotina.utils import find_container
from guillotina.utils import get_content_depth
from guillotina.utils import get_content_path
from zope.interface import implementer

import logging
import typing


logger = logging.getLogger("guillotina")

global_principal_permission_setting = principal_permission_manager.get_setting
global_roles_for_permission = role_permission_manager.get_roles_for_permission


@implementer(ICatalogUtility)
class DefaultSearchUtility:
    async def initialize(self, app):
        """
        initialization
        """

    async def search(self, container: IContainer, query: typing.Any):
        """
        Search parsed query
        """
        return {"member": [], "items_count": 0}

    async def query(self, context: IBaseObject, query: typing.Any):
        """
        Raw search query, uses parser to transform query
        """
        parsed_query = parse_query(context, query, self)
        container = find_container(context)
        if container is not None:
            return await self.search(container, parsed_query)
        raise ContainerNotFound()

    async def aggregation(self, container: IContainer, parsed_query: typing.Any):
        """
        Search aggregation
        """
        return {"member": [], "items_count": 0}

    async def query_aggregation(self, context: IBaseObject, query: typing.Any):
        """
        Raw search query, uses parser to transform query
        """
        parsed_query = parse_query(context, query, self)
        container = find_container(context)
        if container is not None:
            return await self.aggregation(container, parsed_query)
        raise ContainerNotFound()

    async def index(self, container: IContainer, datas):
        """
        {uid: <dict>}
        """

    async def update(self, container: IContainer, datas):
        """
        {uid: <dict>}
        """

    async def remove(self, container: IContainer, uids):
        """
        list of UIDs to remove from index
        """

    async def reindex_all_content(self, context: IBaseObject, security=False):
        """ For all content add a queue task that reindex the object
        """

    async def initialize_catalog(self, container: IContainer):
        """ Creates an index
        """

    async def remove_catalog(self, container: IContainer):
        """ Deletes an index
        """

    async def get_data(self, content, indexes=None, schemas=None):
        data = {}
        adapter = query_adapter(content, ICatalogDataAdapter)
        if adapter:
            data.update(await adapter(indexes, schemas))
        return data


@configure.adapter(for_=IResource, provides=ISecurityInfo)
class DefaultSecurityInfoAdapter(object):
    def __init__(self, content):
        self.content = content

    def __call__(self):
        """ access_users and access_roles """
        return {
            "path": get_content_path(self.content),
            "depth": get_content_depth(self.content),
            "parent_uuid": getattr(getattr(self.content, "__parent__", None), "uuid", None),
            "access_users": get_principals_with_access_content(self.content),
            "access_roles": get_roles_with_access_content(self.content),
            "type_name": self.content.type_name,
            "tid": self.content.__serial__,
            "modification_date": json_compatible(self.content.modification_date),
        }


@configure.adapter(for_=IResource, provides=ICatalogDataAdapter)
class DefaultCatalogDataAdapter(object):
    def __init__(self, content):
        self.content = content
        self.attempts = []  # prevent indexing same data twice

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

    async def __call__(self, indexes=None, schemas=None):
        # For each type
        values = {
            "type_name": self.content.type_name,
            "tid": self.content.__serial__,
            "modification_date": json_compatible(self.content.modification_date),
        }
        if schemas is None:
            schemas = iter_schemata(self.content)

        for schema in schemas:
            try:
                behavior = schema(self.content)
            except TypeError:
                # Content can't adapt to schema, so we don't need to
                # index it anyway. Just continue
                continue

            loaded = False
            for field_name, index_data in merged_tagged_value_dict(schema, index.key).items():
                index_name = index_data.get("index_name", field_name)
                if index_name in values or index_name in self.attempts:
                    # you can override indexers so we do not want to index
                    # the same value more than once
                    continue

                self.attempts.append(index_name)

                try:
                    # accessors we always reindex since we can't know if updated
                    # from the indexes param--they are "fake" like indexes, not fields
                    if "accessor" in index_data:
                        if (
                            indexes is None
                            or not index_data.get("fields")
                            or (len(set(index_data.get("fields", [])) & set(indexes)) > 0)
                        ):
                            if not loaded:
                                await self.load_behavior(behavior)
                                loaded = True
                            values[index_name] = await apply_coroutine(index_data["accessor"], behavior)
                    elif (
                        indexes is None
                        or field_name in indexes
                        or isinstance(getattr(type(self.content), field_name, None), property)
                    ):
                        if not loaded:
                            await self.load_behavior(behavior)
                            loaded = True
                        # in this case, properties are also dynamic so we have to make sure
                        # to allow for them to be reindexed every time.
                        values[index_name] = self.get_data(behavior, schema, field_name)
                except NoIndexField:
                    pass

            for metadata_name in merged_tagged_value_list(schema, metadata.key):
                if (
                    indexes is not None
                    and metadata_name not in indexes
                    and not isinstance(getattr(type(self.content), metadata_name, None), property)
                ):
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
