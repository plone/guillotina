from guillotina import app_settings
from guillotina.catalog.types import BasicParsedQueryInfo
from guillotina.component import get_utilities_for
from guillotina.component import get_utility
from guillotina.component import query_multi_adapter
from guillotina.component import query_utility
from guillotina.content import get_all_possible_schemas_for_type
from guillotina.content import IResourceFactory
from guillotina.directives import index_field
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import merged_tagged_value_list
from guillotina.directives import metadata
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import ISearchParser
from guillotina.utils import execute

import logging
import typing


logger = logging.getLogger("guillotina")


def get_index_fields(type_name):
    mapping = {}
    for schema in get_all_possible_schemas_for_type(type_name):
        # create mapping for content type
        mapping.update(merged_tagged_value_dict(schema, index_field.key))
    return mapping


def get_metadata_fields(type_name):
    fields = []
    for schema in get_all_possible_schemas_for_type(type_name):
        # create mapping for content type
        fields.extend(merged_tagged_value_list(schema, metadata.key))
    return fields


def reindex_in_future(context, security=False):
    """
    Function to reindex a tree of content in the catalog.
    """
    search = query_utility(ICatalogUtility)
    if search is not None:
        execute.in_pool(search.reindex_all_content, context, security).after_request()


_cached_indexes: typing.Dict[str, typing.Dict] = {}


def iter_indexes(invalidate=False) -> typing.Iterator[typing.Tuple[str, typing.Dict]]:
    """
{
    "access_users": ["root"],
    "uuid":"a037df9fa3624b5fb09dbda1480f8210",
    "contributors":null,
    "created":"2017-03-16T08:46:00.633690-05:00",
    "portal_type":"Folder",
    "title":"Posts",
    "modified":"2017-03-16T08:46:00.633690-05:00",
    "depth":2,
    "subjects":null,
    "path":"/container/posts",
    "creators":null,
    "access_roles":["guillotina.SiteAdmin"],
    "parent_uuid":"8406d8b94d0e47bfa6cb0a82e531216b"
}
    """
    if invalidate:
        _cached_indexes.clear()
    if len(_cached_indexes) > 0:
        for f, v in _cached_indexes.items():
            yield f, v

    found: typing.List[str] = []
    for type_name, schema in get_utilities_for(IResourceFactory):
        for field_name, catalog_info in get_index_fields(type_name).items():
            if field_name in found:
                continue
            yield field_name, catalog_info
            found.append(field_name)
            _cached_indexes[field_name] = catalog_info


def get_index_definition(name):
    if len(_cached_indexes) == 0:
        [i for i in iter_indexes()]  # load cache
    if name in _cached_indexes:
        return _cached_indexes[name]


def parse_query(context, query, util=None) -> typing.Optional[BasicParsedQueryInfo]:
    if util is None:
        util = get_utility(ICatalogUtility)
    parser = query_multi_adapter((util, context), ISearchParser, name=app_settings["search_parser"])
    if parser is None:
        logger.warning(f"No parser found for {util}")
        return None
    return parser(query)
