from guillotina.api.content import DefaultGET
from guillotina.auth.users import AnonymousUser
from guillotina.catalog.catalog import DefaultSearchUtility
from guillotina.catalog.utils import parse_query
from guillotina.component import get_utility
from guillotina.const import TRASHED_ID
from guillotina.contrib.catalog.pg import logger
from guillotina.contrib.catalog.pg.indexes import BasicJsonIndex
from guillotina.contrib.catalog.pg.indexes import get_pg_index
from guillotina.contrib.catalog.pg.indexes import get_pg_indexes
from guillotina.contrib.catalog.pg.parser import ParsedQueryInfo
from guillotina.contrib.catalog.pg.utils import sqlq
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import IWriter
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.db.storages.utils import register_sql
from guillotina.db.uid import MAX_UID_LENGTH
from guillotina.exceptions import ContainerNotFound
from guillotina.exceptions import RequestNotFound
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IFolder
from guillotina.interfaces import IPGCatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces.content import IApplication
from guillotina.response import HTTPNotImplemented
from guillotina.transactions import get_transaction
from guillotina.utils import find_container
from guillotina.utils import get_authenticated_user
from guillotina.utils import get_content_path
from guillotina.utils import get_current_request
from guillotina.utils import get_current_transaction
from guillotina.utils import get_object_url
from guillotina.utils import get_roles_principal
from zope.interface import implementer

import asyncpg.exceptions
import json
import orjson
import os
import typing


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

        if os.environ.get("SKIP_PGCATALOG_INIT") or app_settings.get("skip_pgcatalog_init", False):
            return

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

    def get_default_where_clauses(self, context: IBaseObject, unrestricted: bool = False) -> typing.List[str]:
        clauses = []
        sql_wheres = []
        if unrestricted is False:
            users = []
            principal = get_authenticated_user()
            if principal is None:
                # assume anonymous then
                principal = AnonymousUser()

            users.append(principal.id)
            users.extend(principal.groups)
            roles = get_roles_principal(context)

            clauses.extend(
                [
                    "json->'access_users' ?| array['{}']".format("','".join([sqlq(u) for u in users])),
                    "json->'access_roles' ?| array['{}']".format("','".join([sqlq(r) for r in roles])),
                ]
            )
            sql_wheres.append("({})".format(" OR ".join(clauses)))
        container = find_container(context)
        if container is None:
            raise ContainerNotFound()

        sql_wheres.append(f"""json->>'container_id' = '{sqlq(container.id)}'""")
        sql_wheres.append("""type != 'Container'""")
        sql_wheres.append(f"""parent_id != '{sqlq(TRASHED_ID)}'""")
        return sql_wheres

    def build_query(
        self,
        context: IBaseObject,
        query: ParsedQueryInfo,
        select_fields: typing.List[str],
        distinct: typing.Optional[bool] = False,
        unrestricted: bool = False,
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
        where_arg_iter = 0
        # Skip None arguments
        for where in query["wheres"]:
            if isinstance(where, tuple):
                operator, sub_wheres = where
                sub_result = []
                for sub_where in sub_wheres:
                    sub_result.append(sub_where.format(arg=arg_index + where_arg_index))
                    if query["wheres_arguments"][where_arg_iter] is not None:
                        sql_arguments.append(query["wheres_arguments"][where_arg_iter])
                        where_arg_index += 1
                    where_arg_iter += 1
                sql_wheres.append("(" + operator.join(sub_result) + ")")
            else:
                sql_wheres.append(where.format(arg=arg_index + where_arg_index))
                if query["wheres_arguments"][where_arg_iter] is not None:
                    sql_arguments.append(query["wheres_arguments"][where_arg_iter])
                    where_arg_index += 1
                where_arg_iter += 1

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        sql_wheres.extend(self.get_default_where_clauses(context, unrestricted=unrestricted))

        order = (
            order_by_index.order_by_score(query["sort_dir"])
            if query["sort_on_fields"] and hasattr(order_by_index, "order_by_score")
            else order_by_index.order_by(query["sort_dir"])
        )
        sql = """select {} {}
                 from {}
                 where {}
                 {}
                 limit {} offset {}""".format(
            "distinct" if distinct else "",
            ",".join(select_fields),
            sqlq(txn.storage.objects_table_name),
            " AND ".join(sql_wheres),
            "" if distinct else order,
            sqlq(query["size"]),
            sqlq(query["_from"]),
        )
        return sql, sql_arguments

    def build_count_query(
        self, context, query: ParsedQueryInfo, unrestricted: bool = False,
    ) -> typing.Tuple[str, typing.List[typing.Any]]:
        sql_arguments = []
        sql_wheres = []
        select_fields = ["count(*)"]
        arg_index = 1
        for idx, where in enumerate(query["wheres"]):
            sql_wheres.append(where.format(arg=arg_index))
            sql_arguments.append(query["wheres_arguments"][idx])
            arg_index += 1

        sql_wheres.extend(self.get_default_where_clauses(context, unrestricted=unrestricted))

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

    async def aggregation(self, context: IBaseObject, query: ParsedQueryInfo):
        select_fields = [
            "json->'" + sqlq(field) + "' as " + sqlq(field) for field in query["metadata"] or []
        ]  # noqa
        sql, arguments = self.build_query(context, query, select_fields, True)

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
            sql, arguments = self.build_count_query(context, query)
            logger.debug(f"Running search:\n{sql}\n{arguments}")
            async with txn.lock:
                records = await conn.fetch(sql, *arguments)
            total = records[0]["count"]
        return {"items": results, "items_total": total}

    async def search_raw(self, context: IBaseObject, query: typing.Any):
        """
        Search raw query
        """
        raise HTTPNotImplemented()

    async def search(self, context: IBaseObject, query: typing.Any):
        """
        Search query, uses parser to transform query
        """
        parsed_query = parse_query(context, query, self)
        return await self._query(context, parsed_query)  # type: ignore

    async def unrestrictedSearch(self, context: IBaseObject, query: typing.Any):
        """
        Search query without restriction, uses parser to transform query
        """
        parsed_query = parse_query(context, query, self)
        return await self._query(context, parsed_query, True)  # type: ignore

    async def _query(self, context: IResource, query: ParsedQueryInfo, unrestricted: bool = False):
        sql, arguments = self.build_query(context, query, ["id", "zoid", "json"], unrestricted=unrestricted)
        txn = get_current_transaction()
        conn = await txn.get_connection()
        results = []
        fullobjects = query["fullobjects"]
        container = find_container(context)
        if container is None:
            raise ContainerNotFound()

        try:
            context_url = get_object_url(container)
            request = get_current_request()
        except RequestNotFound:
            context_url = get_content_path(container)
            request = None

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
            sql, arguments = self.build_count_query(context, query, unrestricted=unrestricted)
            logger.debug(f"Running search:\n{sql}\n{arguments}")
            async with txn.lock:
                records = await conn.fetch(sql, *arguments)
            total = records[0]["count"]
        return {"items": results, "items_total": total}

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
        json_value = orjson.dumps(json_dict).decode("utf-8")

        statement_sql = txn.storage._sql.get("JSONB_UPDATE", table_name)
        conn = await txn.get_connection()
        async with txn.lock:
            await conn.fetch(statement_sql, oid, json_value)  # The OID of the object  # JSON catalog
