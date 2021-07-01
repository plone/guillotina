from guillotina.catalog.utils import iter_indexes
from guillotina.contrib.catalog.pg.utils import sqlq
from guillotina.db.interfaces import IPostgresStorage

import typing


class BasicJsonIndex:
    operators: typing.List[str] = ["=", "!=", "?", "?|", "is null", "is not null"]

    def __init__(self, name: str):
        self.name = name

    @property
    def idx_name(self) -> str:
        return "idx_objects_{}".format(self.name)

    def get_index_sql(self, storage: IPostgresStorage) -> typing.List[str]:
        return [
            f"""CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
                ON {sqlq(storage.objects_table_name)} ((json->>'{sqlq(self.name)}'));""",
            f"""CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
                ON {sqlq(storage.objects_table_name)} USING gin ((json->'{sqlq(self.name)}'))""",
        ]

    def where(self, value, operator="=") -> str:
        assert operator in self.operators
        if operator in ("?", "?|"):
            return f"""json->'{sqlq(self.name)}' {sqlq(operator)} ${{arg}} """
        if operator in ("is null", "is not null"):
            return f"""(json->>'{sqlq(self.name)}') {sqlq(operator)} """
        else:
            return f"""json->>'{sqlq(self.name)}' {sqlq(operator)} ${{arg}} """

    def order_by(self, direction="ASC") -> str:
        return f"order by json->>'{sqlq(self.name)}' {sqlq(direction)}"

    def select(self) -> typing.List[typing.Any]:
        return []


class BooleanIndex(BasicJsonIndex):
    def get_index_sql(self, storage: IPostgresStorage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
ON {sqlq(storage.objects_table_name)} (((json->>'{sqlq(self.name)}')::boolean));"""
        ]

    def where(self, value, operator="="):
        assert operator in self.operators
        return f"""(json->>'{sqlq(self.name)}')::boolean {sqlq(operator)} ${{arg}}::boolean """


class KeywordIndex(BasicJsonIndex):
    operators = ["?", "?|", "NOT ?", "is null", "is not null"]

    def get_index_sql(self, storage: IPostgresStorage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
ON {sqlq(storage.objects_table_name)} USING gin ((json->'{sqlq(self.name)}'))"""
        ]

    def where(self, value, operator="?"):
        assert operator in self.operators
        not_value = ""
        if operator in ("is null", "is not null"):
            return f"""(json->>'{sqlq(self.name)}') {sqlq(operator)} """
        if "NOT" in operator:
            operator = operator.split()[1]
            not_value = "NOT"
        return f"""{not_value} json->'{sqlq(self.name)}' {sqlq(operator)} ${{arg}} """


class PathIndex(BasicJsonIndex):
    operators = ["="]

    def where(self, value, operator="="):
        assert operator in self.operators
        return f"""
substring(json->>'{sqlq(self.name)}', 0, {len(value) + 1}) {sqlq(operator)} ${{arg}}::text """


class CastIntIndex(BasicJsonIndex):
    cast_type = "integer"
    operators = ["=", "!=", ">", "<", ">=", "<=", "is null", "is not null"]

    def get_index_sql(self, storage: IPostgresStorage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
ON {sqlq(storage.objects_table_name)}
using btree(CAST(json->>'{sqlq(self.name)}' AS {sqlq(self.cast_type)}))"""
        ]

    def where(self, value, operator=">"):
        """
        where CAST(json->>'favorite_count' AS integer) > 5;
        """
        assert operator in self.operators
        if operator in ("is null", "is not null"):
            return f"""(json->>'{sqlq(self.name)}') {sqlq(operator)} """

        return f"""
CAST(json->>'{sqlq(self.name)}' AS {sqlq(self.cast_type)}) {sqlq(operator)} ${{arg}}::{sqlq(self.cast_type)}"""  # noqa

    def order_by(self, direction="ASC") -> str:
        return f"order by json->'{sqlq(self.name)}' {sqlq(direction)}"


class CastFloatIndex(CastIntIndex):
    cast_type = "float"


class CastDateIndex(CastIntIndex):
    cast_type = "timestamp"

    def get_index_sql(self, storage: IPostgresStorage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
ON {sqlq(storage.objects_table_name)} (f_cast_isots(json->>'{sqlq(self.name)}'))"""
        ]

    def where(self, value, operator=">"):
        """
        where CAST(json->>'favorite_count' AS integer) > 5;
        """
        assert operator in self.operators

        if operator in ("is null", "is not null"):
            return f"""(json->>'{sqlq(self.name)}') {sqlq(operator)} """

        return f"""
f_cast_isots(json->>'{sqlq(self.name)}') {sqlq(operator)} ${{arg}}::{sqlq(self.cast_type)}"""

    def order_by_score(self, direction="ASC"):
        return f"order by json->>'{sqlq(self.name)}' {sqlq(direction)}"


class FullTextIndex(BasicJsonIndex):
    operators = ["?", "?|", "=", "is null", "is not null"]

    def get_index_sql(self, storage: IPostgresStorage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}_{sqlq(storage.objects_table_name.replace('.', '_'))}
ON {sqlq(storage.objects_table_name)}
using gin(to_tsvector('simple', json->>'{sqlq(self.name)}'));"""
        ]

    def where(self, value, operator=""):
        """
        to_tsvector(json->>'text') @@ to_tsquery('python & ruby')
        operator is ignored for now...
        """
        if operator in ("is null", "is not null"):
            return f"""(json->>'{sqlq(self.name)}') {sqlq(operator)} """
        if operator == "phrase":
            return f"""
    to_tsvector('simple', json->>'{sqlq(self.name)}') @@ phraseto_tsquery('simple', ${{arg}}::text)"""
        else:
            return f"""
    to_tsvector('simple', json->>'{sqlq(self.name)}') @@ to_tsquery('simple', ${{arg}}::text)"""

    def order_by_score(self, direction="ASC"):
        return f"order by {sqlq(self.name)}_score {sqlq(direction)}"

    def select(self):
        return [
            f"""ts_rank_cd(to_tsvector('simple', json->>'{sqlq(self.name)}'),
                    plainto_tsquery('simple', ${{arg}}::text)) AS {sqlq(self.name)}_score"""
        ]


index_mappings = {
    "*": BasicJsonIndex,
    "keyword": KeywordIndex,
    "textkeyword": KeywordIndex,
    "path": PathIndex,
    "int": CastIntIndex,
    "float": CastFloatIndex,
    "searchabletext": FullTextIndex,
    "text": FullTextIndex,
    "boolean": BooleanIndex,
    "date": CastDateIndex,
}


_cached_indexes: typing.Dict[str, BasicJsonIndex] = {}


def get_pg_indexes(invalidate=False):
    if len(_cached_indexes) > 0:
        return _cached_indexes

    for field_name, catalog_info in iter_indexes():
        catalog_type = catalog_info.get("type", "text")
        if catalog_type not in index_mappings:
            index = index_mappings["*"](field_name)
        else:
            index = index_mappings[catalog_type](field_name)
        _cached_indexes[field_name] = index
    return _cached_indexes


def get_pg_index(name):
    if len(_cached_indexes) == 0:
        get_pg_indexes()
    if name in _cached_indexes:
        return _cached_indexes[name]
