import json
import logging
import typing

from dateutil.parser import parse

from guillotina import configure
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
from guillotina.exceptions import RequestNotFound
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPGCatalogUtility
from guillotina.interfaces import IResource
from guillotina.interfaces import ISearchParser
from guillotina.interfaces.catalog import ICatalogUtility
from guillotina.interfaces.content import IApplication
from guillotina.transactions import get_transaction
from guillotina.utils import find_container
from guillotina.utils import get_authenticated_user
from guillotina.utils import get_content_path
from guillotina.utils import get_object_url
from guillotina.utils import get_security_policy
from zope.interface import implementer


logger = logging.getLogger('guillotina')


app_settings = {
    "load_utilities": {
        "catalog": {
            "provides": "guillotina.interfaces.ICatalogUtility",
            "factory": "guillotina.contrib.catalog.pg.PGSearchUtility"
        }
    }
}


# 2019-06-15T18:37:31.008359+00:00
PG_FUNCTIONS = [
    '''CREATE OR REPLACE FUNCTION f_cast_isots(text)
  RETURNS timestamptz AS
$$SELECT CAST($1 AS timestamptz)$$  -- adapt to your needs
  LANGUAGE sql IMMUTABLE;'''
]


class ParsedQueryInfo(BasicParsedQueryInfo):
    wheres: typing.List[str]
    wheres_arguments: typing.List[typing.Any]
    selects: typing.List[str]
    selects_arguments: typing.List[typing.Any]


_type_mapping = {
    'int': int,
    'float': float
}


@configure.adapter(
    for_=(ICatalogUtility, IResource),
    provides=ISearchParser,
    name='default')
class Parser(BaseParser):

    def __init__(self, util, context):
        self.util = util
        self.context = context

    def process_queried_field(self, field: str, value) -> typing.Optional[
            typing.Tuple[str, typing.Any, typing.Optional[str]]]:
        result: typing.Any = value

        operator = '='
        if field.endswith('__not'):
            operator = '!='
            field = field[:-len('__not')]
        elif field.endswith('__in'):
            operator = '?|'
            field = field[:-len('__in')]
        elif field.endswith('__eq'):
            operator = '='
            field = field[:-len('__eq')]
        elif field.endswith('__gt'):
            operator = '>'
            field = field[:-len('__gt')]
        elif field.endswith('__lt'):
            operator = '<'
            field = field[:-len('__lt')]
        elif field.endswith('__gte'):
            operator = '>='
            field = field[:-len('__gte')]
        elif field.endswith('__lte'):
            operator = '<='
            field = field[:-len('__lte')]

        index = get_index_definition(field)
        if index is None:
            return None

        _type = index['type']
        if _type in _type_mapping:
            try:
                result = _type_mapping[_type](value)
            except ValueError:
                # invalid, can't continue... We could throw query parse error?
                return None
        elif _type == 'date':
            result = parse(value).replace(tzinfo=None)
        elif _type == 'boolean':
            if value in ('true', 'True', 'yes', '1'):
                result = True
            else:
                result = False
        elif _type == 'keyword' and operator not in ('?', '?|'):
            operator = '?'

        if operator == '?|':
            result = to_list(value)

        if operator == '?' and isinstance(result, list):
            operator = '?|'

        pg_index = get_pg_index(field)
        return pg_index.where(result, operator), result, pg_index.select()

    def __call__(self, params: typing.Dict) -> ParsedQueryInfo:
        query_info = super().__call__(params)

        wheres = []
        arguments = []
        selects = []
        selects_arguments = []
        for field, value in query_info['params'].items():
            result = self.process_queried_field(field, value)
            if result is None:
                continue
            sql, value, select = result
            wheres.append(sql)
            arguments.append(value)
            if select is not None:
                selects.append(select)
                selects_arguments.append(value)

        return typing.cast(ParsedQueryInfo, dict(
            query_info,
            wheres=wheres,
            wheres_arguments=arguments,
            selects=selects,
            selects_arguments=selects_arguments,
        ))


class BasicJsonIndex:
    operators: typing.List[str] = ['=', '!=', '?', '?|']

    def __init__(self, name: str):
        self.name = name

    @property
    def idx_name(self) -> str:
        return 'idx_objects_{}'.format(self.name)

    @property
    def index_sql(self) -> typing.List[str]:
        return [
            f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name}
                ON objects ((json->>'{self.name}'));''',
            f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name}
                ON objects USING gin ((json->'{self.name}'))'''
        ]

    def where(self, value, operator='=') -> str:
        assert operator in self.operators
        if operator in ('?', '?|'):
            return f"""json->'{self.name}' {operator} ${{arg}} """
        else:
            return f"""json->>'{self.name}' {operator} ${{arg}} """

    def order_by(self, direction='ASC') -> str:
        return f"order by json->>'{self.name}' {direction}"

    def select(self) -> typing.Optional[str]:
        return None


class BooleanIndex(BasicJsonIndex):
    @property
    def index_sql(self):
        return [f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name}
                    ON objects (((json->>'{self.name}')::boolean));''']

    def where(self, value, operator='='):
        assert operator in self.operators
        return f"""(json->>'{self.name}')::boolean {operator} ${{arg}}::boolean """


class KeywordIndex(BasicJsonIndex):
    operators = ['?', '?|']

    @property
    def index_sql(self):
        return [f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name}
                    ON objects USING gin ((json->'{self.name}'))''']

    def where(self, value, operator='?'):
        assert operator in self.operators
        return f"""json->'{self.name}' {operator} ${{arg}} """


class PathIndex(BasicJsonIndex):
    operators = ['=']

    def where(self, value, operator='='):
        assert operator in self.operators
        return f"""
substring(json->>'{self.name}', 0, {len(value) + 1}) {operator} ${{arg}}::text """


class CastIntIndex(BasicJsonIndex):
    cast_type = 'integer'
    operators = ['=', '!=', '>', '<', '>=', '<=']

    @property
    def index_sql(self):
        return [f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name} ON objects
                    using btree(CAST(json->>'{self.name}' AS {self.cast_type}))''']

    def where(self, value, operator='>'):
        """
        where CAST(json->>'favorite_count' AS integer) > 5;
        """
        assert operator in self.operators
        return f"""
CAST(json->>'{self.name}' AS {self.cast_type}) {operator} ${{arg}}::{self.cast_type}"""


class CastFloatIndex(CastIntIndex):
    cast_type = 'float'


class CastDateIndex(CastIntIndex):
    cast_type = 'timestamp'

    @property
    def index_sql(self):
        return [f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name} ON objects
                    (f_cast_isots(json->>'{self.name}'))''']

    def where(self, value, operator='>'):
        """
        where CAST(json->>'favorite_count' AS integer) > 5;
        """
        assert operator in self.operators
        return f"""
f_cast_isots(json->>'{self.name}') {operator} ${{arg}}::{self.cast_type}"""


class FullTextIndex(BasicJsonIndex):

    @property
    def index_sql(self):
        return [f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name} ON objects
                   using gin(to_tsvector('english', json->>'{self.name}'));''']

    def where(self, value, operator=''):
        """
        to_tsvector('english', json->>'text') @@ to_tsquery('python & ruby')
        operator is ignored for now...
        """
        return f"""
to_tsvector('english', json->>'{self.name}') @@ plainto_tsquery(${{arg}}::text)"""

    def order_by(self, direction='ASC'):
        return f'order by {self.name}_score {direction}'

    def select(self):
        return f'''ts_rank_cd(to_tsvector('english', json->>'{self.name}'),
                   plainto_tsquery(${{arg}}::text)) AS {self.name}_score'''


index_mappings = {
    '*': BasicJsonIndex,
    'keyword': KeywordIndex,
    'textkeyword': KeywordIndex,
    'path': PathIndex,
    'int': CastIntIndex,
    'float': CastFloatIndex,
    'searchabletext': FullTextIndex,
    'text': FullTextIndex,
    'boolean': BooleanIndex,
    'date': CastDateIndex
}


_cached_indexes: typing.Dict[str, BasicJsonIndex] = {}


def get_pg_indexes(invalidate=False):
    if len(_cached_indexes) > 0:
        return _cached_indexes

    for field_name, catalog_info in iter_indexes():
        catalog_type = catalog_info.get('type', 'text')
        if catalog_type not in index_mappings:
            index = index_mappings['*'](field_name)
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

    async def get_data(self, content):
        # we can override and ignore this request since data is already
        # stored in db...
        return {}

    async def initialize(self):
        from guillotina import app_settings
        if not app_settings['store_json']:
            return
        root = get_utility(IApplication, name='root')
        for _id, db in root:
            if not IDatabase.providedBy(db):
                continue
            tm = db.get_transaction_manager()
            if not IPostgresStorage.providedBy(tm.storage):
                continue
            async with tm.storage.pool.acquire() as conn:
                for func in PG_FUNCTIONS:
                    await conn.execute(func)
                for index in [BasicJsonIndex('container_id')] + [v for v in get_pg_indexes().values()]:
                    for sql in index.index_sql:
                        logger.debug(f'Creating index:\n {sql}')
                        await conn.execute(sql)

    def get_default_where_clauses(self, context) -> typing.List[str]:
        users = []
        roles = []
        principal = get_authenticated_user()
        if principal is None:
            # assume anonymous then
            principal = AnonymousUser()
        policy = get_security_policy(principal)

        users.append(principal.id)
        users.extend(principal.groups)
        roles_dict = policy.global_principal_roles(
            principal.id, principal.groups)
        roles.extend([key for key, value in roles_dict.items()
                      if value])

        clauses = [
            "json->'access_users' ?| array['{}']".format(
                "','".join(users)
            ),
            "json->'access_roles' ?| array['{}']".format(
                "','".join(roles)
            )
        ]
        sql_wheres = ['({})'.format(
            ' OR '.join(clauses)
        )]
        # ensure we only query this context
        context_path = get_content_path(context)
        sql_wheres.append("""substring(json->>'path', 0, {}) = '{}'""".format(
            len(context_path) + 1,
            context_path
        ))
        if IContainer.providedBy(context):
            container = context
        else:
            container = find_container(context)  # type: ignore
        if container is not None:
            sql_wheres.append(f"""json->>'container_id' = '{container.id}'""")
        sql_wheres.append("""type != 'Container'""")
        sql_wheres.append(f"""parent_id != '{TRASHED_ID}'""")
        return sql_wheres

    def build_query(self, context,
                    query: ParsedQueryInfo) -> typing.Tuple[str, typing.List[typing.Any]]:
        if query['sort_on'] is None:
            # always need a sort otherwise paging never works
            order_by_index = get_pg_index('uuid')
        else:
            order_by_index = get_pg_index(query['sort_on']) or BasicJsonIndex(query['sort_on'])

        sql_arguments = []
        sql_wheres = []
        select_fields = ['id', 'zoid', 'json']
        arg_index = 1
        for idx, select in enumerate(query['selects']):
            select_fields.append(select.format(arg=arg_index))
            sql_arguments.append(query['selects_arguments'][idx])
            arg_index += 1

        for idx, where in enumerate(query['wheres']):
            sql_wheres.append(where.format(arg=arg_index))
            sql_arguments.append(query['wheres_arguments'][idx])
            arg_index += 1

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        sql_wheres.extend(self.get_default_where_clauses(context))

        sql = '''select {}
                 from {}
                 where {}
                 {}
                 limit {} offset {}'''.format(
            ','.join(select_fields),
            txn.storage._objects_table_name,
            ' AND '.join(sql_wheres),
            order_by_index.order_by(query['sort_dir']),
            query['size'],
            query['_from']
        )
        return sql, sql_arguments

    def build_count_query(self, context,
                          query: ParsedQueryInfo) -> typing.Tuple[str, typing.List[typing.Any]]:
        sql_arguments = []
        sql_wheres = []
        select_fields = ['count(*)']
        arg_index = 1
        for idx, where in enumerate(query['wheres']):
            sql_wheres.append(where.format(arg=arg_index))
            sql_arguments.append(query['wheres_arguments'][idx])
            arg_index += 1

        sql_wheres.extend(self.get_default_where_clauses(context))

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        sql = '''select {}
                 from {}
                 where {}'''.format(
            ','.join(select_fields),
            txn.storage._objects_table_name,
            ' AND '.join(sql_wheres))
        return sql, sql_arguments

    def load_meatdata(self, query: ParsedQueryInfo, data: typing.Dict[str, typing.Any]):
        metadata: typing.Dict[str, typing.Any] = {}
        if query['metadata'] is None:
            metadata = data.copy()
        else:
            for k in query['metadata']:
                if k in data:
                    metadata[k] = data[k]

        for k in (query['excluded_metadata'] or []):
            if k in metadata:
                del metadata[k]
        return metadata

    async def search(self, context, query: ParsedQueryInfo):  # type: ignore
        sql, arguments = self.build_query(context, query)
        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        conn = await txn.get_connection()

        results = []
        try:
            context_url = get_object_url(context)
        except RequestNotFound:
            context_url = get_content_path(context)
        logger.debug(f'Running search:\n{sql}\n{arguments}')
        for record in await conn.fetch(sql, *arguments):
            data = json.loads(record['json'])
            result = self.load_meatdata(query, data)
            result['@name'] = record['id']
            result['@uid'] = record['zoid']
            result['@id'] = data['@absolute_url'] = context_url + data['path']
            results.append(result)

        # also do count...
        total = len(results)
        if total >= query['size']:
            sql, arguments = self.build_count_query(context, query)
            logger.debug(f'Running search:\n{sql}\n{arguments}')
            records = await conn.fetch(sql, *arguments)
            total = records[0]['count']
        return {
            'member': results,
            'total': total
        }

    async def index(self, container, datas):
        '''
        ignored, json storage done for us already
        '''

    async def remove(self, container, uids):
        '''
        ignored, remove done for us already
        '''

    async def reindex_all_content(self, container, security=False):
        """
        recursively go through all content to reindex jsonb...
        """
