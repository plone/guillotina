from guillotina.component import get_utilities_for
from guillotina.content import get_all_possible_schemas_for_type
from guillotina.directives import index
from guillotina.directives import merged_tagged_value_dict
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFactory
from guillotina.utils import get_content_path

import logging


logger = logging.getLogger("guillotina")


class SchemaAnalyzer:
    def __init__(self, context: IResource):
        self.context = context

    def get_request_context(self) -> dict:
        """
        Return current request context (path, id, type_name, title) so the LLM
        can filter by "this container" or resolve references by id/title.
        """
        path = get_content_path(self.context)
        if path != "/" and not path.endswith("/"):
            path = path + "/"
        ctx = {
            "path": path,
            "id": getattr(self.context, "__name__", None) or getattr(self.context, "id", None),
        }
        type_name = getattr(self.context, "type_name", None)
        if type_name:
            ctx["type_name"] = type_name
        title = getattr(self.context, "title", None)
        if title is not None:
            ctx["title"] = title
        return ctx

    async def get_schema_info(self) -> dict:
        """
        Discover all content types, indexed fields, and field types dynamically.
        Returns a dictionary with schema information.
        """
        schema_info = {
            "content_types": {},
            "behaviors": {},
            "field_types": {},
        }

        factories = list(get_utilities_for(IResourceFactory))
        logger.debug(f"Discovered {len(factories)} content type factories")

        for factory_name, factory in factories:
            type_name = factory.type_name
            if type_name is None:
                continue

            type_schema = {}
            schemas = get_all_possible_schemas_for_type(type_name)

            for schema in schemas:
                indices = merged_tagged_value_dict(schema, index.key)
                for field_name, index_info in indices.items():
                    field_type = index_info.get("type", "text")
                    type_schema[field_name] = field_type

            if type_schema:
                schema_info["content_types"][type_name] = type_schema

        behaviors = list(get_utilities_for(IBehavior))
        logger.debug(f"Discovered {len(behaviors)} behaviors")

        for behavior_name, behavior_utility in behaviors:
            behavior_schema = {}
            indices = merged_tagged_value_dict(behavior_utility.interface, index.key)
            for field_name, index_info in indices.items():
                field_type = index_info.get("type", "text")
                behavior_schema[field_name] = field_type

            if behavior_schema:
                schema_info["behaviors"][behavior_name] = behavior_schema

        schema_info["field_types"] = self._categorize_field_types(schema_info)
        schema_info["request_context"] = self.get_request_context()

        return schema_info

    def _categorize_field_types(self, schema_info: dict) -> dict:
        """
        Categorize fields by type for easier query building.
        """
        field_types = {
            "numeric": [],
            "date": [],
            "text": [],
            "keyword": [],
        }

        all_fields = {}
        for type_name, fields in schema_info["content_types"].items():
            for field_name, field_type in fields.items():
                key = f"{type_name}.{field_name}"
                if key not in all_fields:
                    all_fields[key] = field_type

        for key, field_type in all_fields.items():
            if field_type in ("int", "float", "decimal"):
                field_types["numeric"].append(key)
            elif field_type in ("date", "datetime"):
                field_types["date"].append(key)
            elif field_type == "keyword":
                field_types["keyword"].append(key)
            else:
                field_types["text"].append(key)

        return field_types
