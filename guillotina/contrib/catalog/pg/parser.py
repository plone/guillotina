from dateutil.parser import parse
from guillotina import configure
from guillotina.catalog.parser import BaseParser
from guillotina.catalog.parser import to_list
from guillotina.catalog.types import BasicParsedQueryInfo
from guillotina.catalog.utils import get_index_definition
from guillotina.contrib.catalog.pg import logger
from guillotina.contrib.catalog.pg.indexes import get_pg_index
from guillotina.interfaces import IResource
from guillotina.interfaces import ISearchParser
from guillotina.interfaces.catalog import ICatalogUtility

import typing
import urllib


_type_mapping = {"int": int, "float": float}


class ParsedQueryInfo(BasicParsedQueryInfo):
    sort_on_fields: bool
    wheres: typing.List[typing.Any]
    wheres_arguments: typing.List[typing.Any]
    selects: typing.List[str]
    selects_arguments: typing.List[typing.Any]


@configure.adapter(for_=(ICatalogUtility, IResource), provides=ISearchParser, name="default")
class Parser(BaseParser):
    def process_compound_field(self, field, value, operator):
        parsed_value = urllib.parse.parse_qsl(urllib.parse.unquote(value))
        if not isinstance(parsed_value, list):
            return None
        wheres = []
        arguments = []
        selects = []
        for sfield, svalue in parsed_value:
            result = self.process_queried_field(sfield, svalue)
            if result is not None:
                wheres.append(result[0])
                arguments.extend(result[1])
                selects.extend(result[2])
        if len(wheres) > 0:
            return (operator, wheres), arguments, selects, field

    def process_queried_field(
        self, field: str, value
    ) -> typing.Optional[typing.Tuple[typing.Any, typing.List[typing.Any], typing.List[str], str]]:
        # compound field support
        if field.endswith("__or"):
            return self.process_compound_field(field, value, " OR ")
        elif field.endswith("__and"):
            field = field[: -len("__and")]
            return self.process_compound_field(field, value, " AND ")

        result: typing.Any = value

        operator = "="
        if field.endswith("__not"):
            if value == "null":
                operator = "is not null"
            else:
                operator = "!="
            field = field[: -len("__not")]
        elif field.endswith("__in"):
            operator = "?|"
            field = field[: -len("__in")]
        elif field.endswith("__eq"):
            operator = "="
            field = field[: -len("__eq")]
        elif field.endswith("__gt"):
            operator = ">"
            field = field[: -len("__gt")]
        elif field.endswith("__lt"):
            operator = "<"
            field = field[: -len("__lt")]
        elif field.endswith("__gte"):
            operator = ">="
            field = field[: -len("__gte")]
        elif field.endswith("__lte"):
            operator = "<="
            field = field[: -len("__lte")]
        elif field.endswith("__starts"):
            operator = "starts"
            field = field[: -len("__starts")]

        index = get_index_definition(field)
        if index is None:
            return None

        _type = index["type"]
        if _type in _type_mapping:
            try:
                result = _type_mapping[_type](value)
            except ValueError:
                # invalid, can't continue... We could throw query parse error?
                return None
        elif _type == "date":
            result = parse(value).replace(tzinfo=None)
        elif _type == "boolean":
            if value in ("true", "True", "yes", "1"):
                result = True
            else:
                result = False
        elif _type == "keyword" and operator not in ("?", "?|", "is not null"):
            if operator == "!=":
                operator = "NOT ?"
            else:
                operator = "?"
        elif _type in ("text", "searchabletext") and operator != "is not null":
            if " " in value:
                operator = "phrase"
                result = "&".join(to_list(value))
            else:
                operator = "="
                result = f"{value}:*"
        if _type == "path" and operator != "is not null":
            if operator != "starts":
                # we do not currently support other search types
                logger.warning(f"Unsupported search {field}: {value}")
            operator = "="

        if operator == "?|":
            result = to_list(value)

        if operator == "?" and isinstance(result, list):
            operator = "?|"
        elif operator == "NOT ?" and isinstance(result, list):
            operator = "NOT ?|"

        if value == "null":
            result = None
            if operator != "is not null":
                operator = "is null"

        pg_index = get_pg_index(field)
        return pg_index.where(result, operator), [result], pg_index.select(), field

    def __call__(self, params: typing.Dict) -> ParsedQueryInfo:
        query_info = super().__call__(params)
        wheres: typing.List[str] = []
        arguments: typing.List[str] = []
        selects: typing.List[str] = []
        selects_arguments: typing.List[str] = []
        sort_field = query_info.get("sort_on", None)
        sort_on_fields = False
        for field, value in query_info["params"].items():
            result = self.process_queried_field(field, value)
            if result is None:
                continue
            sql, values, select, field = result
            if sort_field is not None and field == sort_field:
                sort_on_fields = True
            wheres.append(sql)
            arguments.extend(values)
            if select:
                selects.extend(select)
                selects_arguments.extend(values)

        return typing.cast(
            ParsedQueryInfo,
            dict(
                query_info,
                sort_on_fields=sort_on_fields,
                wheres=wheres,
                wheres_arguments=arguments,
                selects=selects,
                selects_arguments=selects_arguments,
            ),
        )
