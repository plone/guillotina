from guillotina.content import iter_schemata_for_type
from guillotina.directives import index
from guillotina.directives import merged_tagged_value_dict
from guillotina.directives import merged_tagged_value_list
from guillotina.directives import metadata


def get_index_fields(type_name):
    mapping = {}
    for schema in iter_schemata_for_type(type_name):
        # create mapping for content type
        mapping.update(merged_tagged_value_dict(schema, index.key))
    return mapping


def get_metadata_fields(type_name):
    fields = []
    for schema in iter_schemata_for_type(type_name):
        # create mapping for content type
        fields.extend(merged_tagged_value_list(schema, metadata.key))
    return fields
