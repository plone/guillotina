from dateutil.parser import parse
from guillotina import configure
from guillotina.api.content import DefaultGET
from guillotina.auth.users import AnonymousUser
from guillotina.catalog.catalog import DefaultSearchUtility
from guillotina.catalog.parser import BaseParser
from guillotina.catalog.parser import to_list
from guillotina.catalog.types import BasicParsedQueryInfo
from guillotina.catalog.utils import get_index_definition
from guillotina.catalog.utils import iter_indexes
from guillotina.component import get_utility
from guillotina.const import TRASHED_ID
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import IWriter
from guillotina.db.storages.utils import register_sql
from guillotina.db.uid import MAX_UID_LENGTH
from guillotina.exceptions import RequestNotFound
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IFolder
from guillotina.interfaces import IPGCatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces import ISearchParser
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.interfaces.content import IApplication
from guillotina.transactions import get_transaction
from guillotina.utils import get_authenticated_user
from guillotina.utils import get_content_path
from guillotina.utils import get_current_request
from guillotina.utils import get_current_transaction
from guillotina.utils import get_object_url
from guillotina.utils import get_security_policy
from zope.interface import implementer

import asyncpg.exceptions
import json
import logging
import typing
import ujson


logger = logging.getLogger("guillotina")


app_settings = {
    "load_utilities": {
        "catalog": {
            "provides": "guillotina.interfaces.ICatalogUtility",
            "factory": "guillotina.contrib.catalog.pg.PGSearchUtility",
        }
    }
}


# 2019-06-15T18:37:31.008359+00:00
PG_FUNCTIONS = [
    """CREATE OR REPLACE FUNCTION f_cast_isots(text) RETURNS timestamptz AS $$
begin
    return CAST($1 AS timestamptz);
exception
    when invalid_text_representation then
        return CAST('1970-01-01T00:00:00Z' AS timestamptz);
    when datetime_field_overflow then
        return CAST('1970-01-01T00:00:00Z' AS timestamptz);
end;
$$ language plpgsql immutable;
"""
]

# Reindex logic
register_sql(
    "JSONB_UPDATE",
    f"""
UPDATE {{table_name}}
SET
    json = $2::json
WHERE
    zoid = $1::varchar({MAX_UID_LENGTH})""",
)


class ParsedQueryInfo(BasicParsedQueryInfo):
    wheres: typing.List[typing.Any]
    wheres_arguments: typing.List[typing.Any]
    selects: typing.List[str]
    selects_arguments: typing.List[typing.Any]


_type_mapping = {"int": int, "float": float}

_sql_replacements = (("'", "''"), ("\\", "\\\\"), ("\x00", ""))


def sqlq(v):
    """
    Escape sql...

    We use sql arguments where we don't control the information but let's
    be extra careful anyways...
    """
    if not isinstance(v, (bytes, str)):
        return v
    for value, replacement in _sql_replacements:
        v = v.replace(value, replacement)
    return v


@configure.adapter(for_=(ICatalogUtility, IResource), provides=ISearchParser, name="default")
class Parser(BaseParser):
    def process_compound_field(self, field, value, operator):
        if not isinstance(value, dict):
            return None
        wheres = []
        arguments = []
        selects = []
        for sfield, svalue in value.items():
            result = self.process_queried_field(sfield, svalue)
            if result is not None:
                wheres.append(result[0])
                arguments.extend(result[1])
                selects.extend(result[2])
        if len(wheres) > 0:
            return (operator, wheres), arguments, selects

    def process_queried_field(
        self, field: str, value
    ) -> typing.Optional[typing.Tuple[typing.Any, typing.List[typing.Any], typing.List[str]]]:
        # compound field support
        if field.endswith("__or"):
            return self.process_compound_field(field, value, " OR ")
        elif field.endswith("__and"):
            field = field[: -len("__and")]
            return self.process_compound_field(field, value, " AND ")

        result: typing.Any = value

        operator = "="
        if field.endswith("__not"):
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
        elif _type == "keyword" and operator not in ("?", "?|"):
            operator = "?"
        elif _type in ("text", "searchabletext"):
            operator = "="
            value = "&".join(to_list(value))
        if _type == "path":
            if operator != "starts":
                # we do not currently support other search types
                logger.warning(f"Unsupported search {field}: {value}")
            operator = "="

        if operator == "?|":
            result = to_list(value)

        if operator == "?" and isinstance(result, list):
            operator = "?|"

        pg_index = get_pg_index(field)
        return pg_index.where(result, operator), [result], pg_index.select()

    def __call__(self, params: typing.Dict) -> ParsedQueryInfo:
        query_info = super().__call__(params)

        wheres = []
        arguments = []
        selects = []
        selects_arguments = []
        for field, value in query_info["params"].items():
            result = self.process_queried_field(field, value)
            if result is None:
                continue
            sql, values, select = result
            wheres.append(sql)
            arguments.extend(values)
            if select:
                selects.extend(select)
                selects_arguments.extend(values)

        return typing.cast(
            ParsedQueryInfo,
            dict(
                query_info,
                wheres=wheres,
                wheres_arguments=arguments,
                selects=selects,
                selects_arguments=selects_arguments,
            ),
        )


class BasicJsonIndex:
    operators: typing.List[str] = ["=", "!=", "?", "?|"]

    def __init__(self, name: str):
        self.name = name

    @property
    def idx_name(self) -> str:
        return "idx_objects_{}".format(self.name)

    def get_index_sql(self, storage: IPostgresStorage) -> typing.List[str]:
        return [
            f"""CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
                ON {sqlq(storage.objects_table_name)} ((json->>'{sqlq(self.name)}'));""",
            f"""CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
                ON {sqlq(storage.objects_table_name)} USING gin ((json->'{sqlq(self.name)}'))""",
        ]

    def where(self, value, operator="=") -> str:
        assert operator in self.operators
        if operator in ("?", "?|"):
            return f"""json->'{sqlq(self.name)}' {sqlq(operator)} ${{arg}} """
        else:
            return f"""json->>'{sqlq(self.name)}' {sqlq(operator)} ${{arg}} """

    def order_by(self, direction="ASC") -> str:
        return f"order by json->>'{sqlq(self.name)}' {sqlq(direction)}"

    def select(self) -> typing.List[typing.Any]:
        return []


class BooleanIndex(BasicJsonIndex):
    def get_index_sql(self, storage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
ON {sqlq(storage.objects_table_name)} (((json->>'{sqlq(self.name)}')::boolean));"""
        ]

    def where(self, value, operator="="):
        assert operator in self.operators
        return f"""(json->>'{sqlq(self.name)}')::boolean {sqlq(operator)} ${{arg}}::boolean """


class KeywordIndex(BasicJsonIndex):
    operators = ["?", "?|"]

    def get_index_sql(self, storage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
ON {sqlq(storage.objects_table_name)} USING gin ((json->'{sqlq(self.name)}'))"""
        ]

    def where(self, value, operator="?"):
        assert operator in self.operators
        return f"""json->'{sqlq(self.name)}' {sqlq(operator)} ${{arg}} """


class PathIndex(BasicJsonIndex):
    operators = ["="]

    def where(self, value, operator="="):
        assert operator in self.operators
        return f"""
substring(json->>'{sqlq(self.name)}', 0, {len(value) + 1}) {sqlq(operator)} ${{arg}}::text """


class CastIntIndex(BasicJsonIndex):
    cast_type = "integer"
    operators = ["=", "!=", ">", "<", ">=", "<="]

    def get_index_sql(self, storage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
ON {sqlq(storage.objects_table_name)}
using btree(CAST(json->>'{sqlq(self.name)}' AS {sqlq(self.cast_type)}))"""
        ]

    def where(self, value, operator=">"):
        """
        where CAST(json->>'favorite_count' AS integer) > 5;
        """
        assert operator in self.operators
        return f"""
CAST(json->>'{sqlq(self.name)}' AS {sqlq(self.cast_type)}) {sqlq(operator)} ${{arg}}::{sqlq(self.cast_type)}"""  # noqa


class CastFloatIndex(CastIntIndex):
    cast_type = "float"


class CastDateIndex(CastIntIndex):
    cast_type = "timestamp"

    def get_index_sql(self, storage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
ON {sqlq(storage.objects_table_name)} (f_cast_isots(json->>'{sqlq(self.name)}'))"""
        ]

    def where(self, value, operator=">"):
        """
        where CAST(json->>'favorite_count' AS integer) > 5;
        """
        assert operator in self.operators
        return f"""
f_cast_isots(json->>'{sqlq(self.name)}') {sqlq(operator)} ${{arg}}::{sqlq(self.cast_type)}"""


class FullTextIndex(BasicJsonIndex):
    operators = ["?", "?|", "="]

    def get_index_sql(self, storage):
        return [
            f"""
CREATE INDEX CONCURRENTLY IF NOT EXISTS {sqlq(self.idx_name)}
ON {sqlq(storage.objects_table_name)}
using gin(to_tsvector('english', json->>'{sqlq(self.name)}'));"""
        ]

    def where(self, value, operator=""):
        """
        to_tsvector('english', json->>'text') @@ to_tsquery('python & ruby')
        operator is ignored for now...
        """
        return f"""
to_tsvector('english', json->>'{sqlq(self.name)}') @@ plainto_tsquery(${{arg}}::text)"""

    def order_by(self, direction="ASC"):
        return f"order by {sqlq(self.name)}_score {sqlq(direction)}"

    def select(self):
        return [
            f"""ts_rank_cd(to_tsvector('english', json->>'{sqlq(self.name)}'),
                    plainto_tsquery(${{arg}}::text)) AS {sqlq(self.name)}_score"""
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


@implementer(IPGCatalogUtility)
class PGSearchUtility(DefaultSearchUtility):
    """
    Indexes are transparently maintained in the database so all indexing
    operations can be ignored
    """

    async def get_data(self, content, indexes=None, schemas=None):
        # we can override and ignore this request since data is already
        # stored in db...
        return {}

    async def initialize(self, app=None):
        from guillotina import app_settings

        if not app_settings["store_json"]:
            return
        root = get_utility(IApplication, name="root")
        for _id, db in root:
            if not IDatabase.providedBy(db):
                continue
            tm = db.get_transaction_manager()
            if not IPostgresStorage.providedBy(tm.storage):
                continue
            try:
                async with tm.storage.pool.acquire() as conn:
                    for func in PG_FUNCTIONS:
                        await conn.execute(func)
                    for index in [BasicJsonIndex("container_id")] + [v for v in get_pg_indexes().values()]:
                        sqls = index.get_index_sql(tm.storage)
                        for sql in sqls:
                            logger.debug(f"Creating index:\n {sql}")
                            await conn.execute(sql)
            except asyncpg.exceptions.ConnectionDoesNotExistError:  # pragma: no cover
                # closed before it could be setup
                pass
            except AttributeError as ex:  # pragma: no cover
                if "'reset'" in str(ex):
                    # ignore error removing from pool if already closed
                    return
                raise

    def get_default_where_clauses(self, container: IContainer) -> typing.List[str]:
        users = []
        roles = []
        principal = get_authenticated_user()
        if principal is None:
            # assume anonymous then
            principal = AnonymousUser()
        policy = get_security_policy(principal)

        users.append(principal.id)
        users.extend(principal.groups)
        roles_dict = policy.global_principal_roles(principal.id, principal.groups)
        roles.extend([key for key, value in roles_dict.items() if value])

        clauses = [
            "json->'access_users' ?| array['{}']".format("','".join([sqlq(u) for u in users])),
            "json->'access_roles' ?| array['{}']".format("','".join([sqlq(r) for r in roles])),
        ]
        sql_wheres = ["({})".format(" OR ".join(clauses))]
        sql_wheres.append(f"""json->>'container_id' = '{sqlq(container.id)}'""")
        sql_wheres.append("""type != 'Container'""")
        sql_wheres.append(f"""parent_id != '{sqlq(TRASHED_ID)}'""")
        return sql_wheres

    def build_query(
        self,
        container: IContainer,
        query: ParsedQueryInfo,
        select_fields: typing.List[str],
        distinct: typing.Optional[bool] = False,
    ) -> typing.Tuple[str, typing.List[typing.Any]]:
        if query["sort_on"] is None:
            # always need a sort otherwise paging never works
            order_by_index = get_pg_index("uuid")
        else:
            order_by_index = get_pg_index(query["sort_on"]) or BasicJsonIndex(query["sort_on"])

        sql_arguments = []
        sql_wheres = []
        arg_index = 1
        for idx, select in enumerate(query["selects"]):
            select_fields.append(select.format(arg=arg_index))
            sql_arguments.append(query["selects_arguments"][idx])
            arg_index += 1

        where_arg_index = 0
        for where in query["wheres"]:
            if isinstance(where, tuple):
                operator, sub_wheres = where
                sub_result = []
                for sub_where in sub_wheres:
                    sub_result.append(sub_where.format(arg=arg_index + where_arg_index))
                    sql_arguments.append(query["wheres_arguments"][where_arg_index])
                    where_arg_index += 1
                sql_wheres.append("(" + operator.join(sub_result) + ")")
            else:
                sql_wheres.append(where.format(arg=arg_index + where_arg_index))
                sql_arguments.append(query["wheres_arguments"][where_arg_index])
                where_arg_index += 1

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        sql_wheres.extend(self.get_default_where_clauses(container))

        sql = """select {} {}
                 from {}
                 where {}
                 {}
                 limit {} offset {}""".format(
            "distinct" if distinct else "",
            ",".join(select_fields),
            sqlq(txn.storage.objects_table_name),
            " AND ".join(sql_wheres),
            "" if distinct else order_by_index.order_by(query["sort_dir"]),
            sqlq(query["size"]),
            sqlq(query["_from"]),
        )
        return sql, sql_arguments

    def build_count_query(
        self, context, query: ParsedQueryInfo
    ) -> typing.Tuple[str, typing.List[typing.Any]]:
        sql_arguments = []
        sql_wheres = []
        select_fields = ["count(*)"]
        arg_index = 1
        for idx, where in enumerate(query["wheres"]):
            sql_wheres.append(where.format(arg=arg_index))
            sql_arguments.append(query["wheres_arguments"][idx])
            arg_index += 1

        sql_wheres.extend(self.get_default_where_clauses(context))

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        sql = """select {}
                 from {}
                 where {}""".format(
            ",".join(select_fields), sqlq(txn.storage.objects_table_name), " AND ".join(sql_wheres)
        )
        return sql, sql_arguments

    def load_meatdata(self, query: ParsedQueryInfo, data: typing.Dict[str, typing.Any]):
        metadata: typing.Dict[str, typing.Any] = {}
        if query["metadata"] is None:
            metadata = data.copy()
        else:
            for k in query["metadata"]:
                if k in data:
                    metadata[k] = data[k]

        for k in query["excluded_metadata"] or []:
            if k in metadata:
                del metadata[k]
        return metadata

    async def aggregation(self, container: IContainer, query: ParsedQueryInfo):
        select_fields = [
            "json->'" + sqlq(field) + "' as " + sqlq(field) for field in query["metadata"] or []
        ]  # noqa
        sql, arguments = self.build_query(container, query, select_fields, True)

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        conn = await txn.get_connection()

        results = []
        logger.debug(f"Running search:\n{sql}\n{arguments}")
        async with txn.lock:
            records = await conn.fetch(sql, *arguments)
        for record in records:
            results.append([json.loads(record[field]) for field in query["metadata"] or []])

        total = len(results)
        if total >= query["size"] or query["_from"] != 0:
            sql, arguments = self.build_count_query(container, query)
            logger.debug(f"Running search:\n{sql}\n{arguments}")
            async with txn.lock:
                records = await conn.fetch(sql, *arguments)
            total = records[0]["count"]
        return {"member": results, "items_count": total}

    async def search(self, container: IContainer, query: ParsedQueryInfo):  # type: ignore
        sql, arguments = self.build_query(container, query, ["id", "zoid", "json"])
        txn = get_current_transaction()
        conn = await txn.get_connection()

        results = []
        fullobjects = query["fullobjects"]
        try:
            context_url = get_object_url(container)
            request = get_current_request()
        except RequestNotFound:
            context_url = get_content_path(container)
            request = None
            txn = None
        logger.debug(f"Running search:\n{sql}\n{arguments}")
        async with txn.lock:
            records = await conn.fetch(sql, *arguments)
        for record in records:
            data = json.loads(record["json"])
            if fullobjects and request is not None and txn is not None:
                # Get Object
                obj = await txn.get(data["uuid"])
                # Serialize object
                view = DefaultGET(obj, request)
                result = await view()
            else:
                result = self.load_meatdata(query, data)
                result["@name"] = record["id"]
                result["@uid"] = record["zoid"]
                result["@id"] = data["@absolute_url"] = context_url + data["path"]
            results.append(result)

        # also do count...
        total = len(results)
        if total >= query["size"] or query["_from"] != 0:
            sql, arguments = self.build_count_query(container, query)
            logger.debug(f"Running search:\n{sql}\n{arguments}")
            async with txn.lock:
                records = await conn.fetch(sql, *arguments)
            total = records[0]["count"]
        return {"member": results, "items_count": total}

    async def index(self, container, datas):
        """
        ignored, json storage done for us already
        """

    async def remove(self, container, uids):
        """
        ignored, remove done for us already
        """

    async def reindex_all_content(self, container, security=False):
        """
        recursively go through all content to reindex jsonb...
        """

        data = {"count": 0, "transaction": None, "transactions": 0, "tm": get_current_transaction()._manager}

        try:
            data["table_name"] = data["tm"]._storage._objects_table_name
        except AttributeError:
            # Not supported DB
            return

        data["transaction"] = await data["tm"].begin()
        container.__txn__ = data["transaction"]
        await self._process_object(container, data)
        if IFolder.providedBy(container):
            await self._process_folder(container, data)
        await data["tm"].commit(txn=data["transaction"])

    async def _process_folder(self, obj, data):
        for key in await obj.async_keys():
            try:
                item = await data["transaction"].get_child(obj, key)
            except (KeyError, ModuleNotFoundError):
                continue
            if item is None:
                continue
            await self._process_object(item, data)

    async def _process_object(self, obj, data):

        if data["count"] % 200 == 0:
            await data["tm"].commit(txn=data["transaction"])
            data["transaction"] = await data["tm"].begin()
            obj.__txn__ = data["transaction"]

        uuid = obj.__uuid__

        writer = IWriter(obj)
        await self._index(uuid, writer, data["transaction"], data["table_name"])

        data["count"] += 1

        if IFolder.providedBy(obj):
            await self._process_folder(obj, data)
        del obj

    async def _index(self, oid, writer, txn: ITransaction, table_name):
        json_dict = await writer.get_json()
        json_value = ujson.dumps(json_dict)

        statement_sql = txn.storage._sql.get("JSONB_UPDATE", table_name)
        conn = await txn.get_connection()
        async with txn.lock:
            await conn.fetch(statement_sql, oid, json_value)  # The OID of the object  # JSON catalog
