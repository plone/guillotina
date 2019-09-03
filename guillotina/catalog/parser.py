from guillotina.catalog.types import BasicParsedQueryInfo
from guillotina.catalog.utils import iter_indexes
from guillotina.utils import get_content_depth
from guillotina.utils import get_content_path

import typing


def to_list(value: typing.Union[str, list]) -> typing.List[str]:
    if isinstance(value, str):
        value = value.split(",")
    if not isinstance(value, list):
        value = [value]
    return value


class BaseParser:
    def __init__(self, util, context):
        self.util = util
        self.context = context

    def __call__(self, params: typing.Dict) -> BasicParsedQueryInfo:
        # bbb
        if "SearchableText" in params:
            value = params.pop("SearchableText")
            oring = {}
            for index_name, idx_data in iter_indexes():
                if idx_data["type"] in ("text", "searchabletext"):
                    oring["{}__in".format(index_name)] = value
            params["searchabletext__or"] = oring

        if params.get("sort_on") == "getObjPositionInParent":
            params["_sort_asc"] = "position_in_parent"
            del params["sort_on"]

        if "b_size" in params:
            if "b_start" in params:
                params["_from"] = params.pop("b_start")
            params["_size"] = params.pop("b_size")

        if "path.depth" in params:
            params["depth"] = params.pop("path.depth")

        if "portal_type" in params:
            params["type_name"] = params.pop("portal_type")

        if "_fullobjects" in params:
            fullobjects = True
        else:
            fullobjects = False

        _from = 0
        size = 20
        sort_field = None
        sort_dir = "ASC"

        # normalize depth
        found = False
        for param in [k for k in params.keys()]:
            if param == "depth" or param.startswith("depth__"):
                found = True
                params[param] = str(int(params[param]) + get_content_depth(self.context))
        if not found:
            # default to a depth so we don't show container
            params["depth__gte"] = str(1 + get_content_depth(self.context))

        # From
        if "_from" in params:
            try:
                _from = int(params.pop("_from"))
            except ValueError:
                _from = 0

        # Sort
        if "_sort_asc" in params:
            sort_field = params.pop("_sort_asc")
            sort_dir = "ASC"
        elif "_sort_des" in params:
            sort_field = params.pop("_sort_des")
            sort_dir = "DESC"

        # Path specific use case
        if "path__starts" in params:
            path = params.pop("path__starts")
            path = "/" + path.strip("/")
        else:
            path = get_content_path(self.context)
        params["path__starts"] = path

        if "_size" in params:
            try:
                size = min(int(params.pop("_size")), 50)
            except ValueError:
                pass

        # Metadata
        metadata = None
        if params.get("_metadata") or params.get("metadata_fields"):
            fields: str = typing.cast(str, params.get("_metadata") or params.get("metadata_fields"))
            if "_all" not in fields:
                metadata = to_list(fields)
            params.pop("_metadata", None)
            params.pop("metadata_fields", None)

        excluded_metadata = None
        if params.get("_metadata_not"):
            excluded_metadata = to_list(params.pop("_metadata_not"))

        return {
            "_from": _from,
            "size": size,
            "sort_on": sort_field,
            "sort_dir": sort_dir,
            "metadata": metadata,
            "fullobjects": fullobjects,
            "excluded_metadata": excluded_metadata,
            "params": params,
        }
