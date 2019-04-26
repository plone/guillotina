from guillotina.component import query_utility
from guillotina.content import get_all_possible_schemas_for_type
from guillotina.directives import index
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import merged_tagged_value_list
from guillotina.directives import metadata
from guillotina.interfaces import ICatalogUtility
from guillotina.utils import execute


def get_index_fields(type_name):
    mapping = {}
    for schema in get_all_possible_schemas_for_type(type_name):
        # create mapping for content type
        mapping.update(merged_tagged_value_dict(schema, index.key))
    return mapping


def get_metadata_fields(type_name):
    fields = []
    for schema in get_all_possible_schemas_for_type(type_name):
        # create mapping for content type
        fields.extend(merged_tagged_value_list(schema, metadata.key))
    return fields


def reindex_in_future(context, request, security=False):
    '''
    Function to reindex a tree of content in the catalog.
    '''
    search = query_utility(ICatalogUtility)
    if search is not None:
        execute.in_pool(
            search.reindex_all_content,
            context, security,
            request=request).after_request()
