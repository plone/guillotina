import json
from guillotina.const import TRASHED_ID
import logging
import typing

from dateutil.parser import parse

from guillotina import configure
from guillotina.auth.users import AnonymousUser
from guillotina.catalog.catalog import DefaultSearchUtility
from guillotina.catalog.utils import get_index_definition
from guillotina.catalog.utils import iter_indexes
from guillotina.component import get_utility
from guillotina.db.interfaces import IPostgresStorage
from guillotina.db.storages.utils import clear_table_name
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
from guillotina.utils import get_content_depth
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


def to_list(value):
    if isinstance(value, str):
        value = value.split(',')
    if not isinstance(value, list):
        value = [value]
    return value


def process_queried_field(field: str, value) -> typing.Optional[
        typing.Tuple[str, typing.Any, typing.Optional[str]]]:
    result: typing.Any = value

    operator = '='
    if field == 'portal_type':
        # XXX: Compatibility with plone?
        field = 'type_name'

    if field.endswith('__not'):
        operator = '!='
        field = field.rstrip('__not')
    elif field.endswith('__in'):
        operator = '?|'
        field = field.rstrip('__in')
    elif field.endswith('__eq'):
        operator = '='
        field = field.rstrip('__eq')
    elif field.endswith('__gt'):
        operator = '>'
        field = field.rstrip('__gt')
    elif field.endswith('__lt'):
        operator = '<'
        field = field.rstrip('__lt')
    elif field.endswith('__gte'):
        operator = '>='
        field = field.rstrip('__gte')
    elif field.endswith('__lte'):
        operator = '<='
        field = field.rstrip('__lte')

    if field == 'portal_type':
        # XXX: Compatibility with plone?
        field = 'type_name'

    index = get_index_definition(field)
    if index is None:
        return None

    _type = index['type']
    if _type == 'int':
        try:
            result = int(value)
        except ValueError:
            pass
    elif _type == 'date':
        result = parse(value).replace(tzinfo=None)
    elif _type == 'boolean':
        if value in ('true', 'True', 'yes', '1'):
            result = True
        else:
            result = False
    elif _type == 'keyword':
        operator = '?'

    if operator == '?|':
        result = to_list(value)

    if operator == '?' and isinstance(result, list):
        operator = '?|'

    pg_index = get_pg_index(field)
    return pg_index.where(result, operator), result, pg_index.select()


def bbb_parser(get_params):

    if 'SearchableText' in get_params:
        value = get_params.pop('SearchableText')
        for index_name, idx_data in iter_indexes():
            if idx_data['type'] in ('text', 'searchabletext'):
                get_params['{}__in'.format(index_name)] = value

    if get_params.get('sort_on') == 'getObjPositionInParent':
        get_params['_sort_asc'] = 'position_in_parent'
        del get_params['sort_on']

    if 'b_size' in get_params:
        if 'b_start' in get_params:
            get_params['_from'] = get_params['b_start']
            del get_params['b_start']
        get_params['_size'] = get_params['b_size']
        del get_params['b_size']

    if 'path.depth' in get_params:
        get_params['depth'] = get_params['path.depth']
        del get_params['path.depth']


class ParsedQueryInfo(typing.NamedTuple):
    sort_on: typing.Optional[str]
    sort_dir: typing.Optional[str]
    wheres: typing.List[str]
    wheres_arguments: typing.List[typing.Any]
    selects: typing.List[str]
    selects_arguments: typing.List[typing.Any]
    from_: int
    size: int
    full_objects: bool


@configure.adapter(
    for_=(ICatalogUtility, IResource),
    provides=ISearchParser,
    name='default')
class Parser:

    def __init__(self, util, context):
        self.util = util
        self.context = context

    def __call__(self, params: typing.Dict) -> ParsedQueryInfo:
        # Fullobject
        full_objects = params.pop('_fullobject', False)

        bbb_parser(params)
        from_ = 0
        size = 20
        sort_field = None
        sort_dir = 'ASC'

        # normalize depth
        found = False
        for param in params.keys():
            if param == 'depth' or param.startswith('depth__'):
                found = True
                params[param] = str(int(params[param]) + get_content_depth(self.context))
        if not found:
            # default to a depth so we don't show container
            params['depth__gte'] = str(1 + get_content_depth(self.context))

        # From
        if '_from' in params:
            try:
                from_ = params.pop('_from')
            except ValueError:
                pass

        # Sort
        if '_sort_asc' in params:
            sort_field = params.pop('_sort_asc')
            sort_dir = 'ASC'
        elif '_sort_des' in params:
            sort_field = params.pop('_sort_des')
            sort_dir = 'DESC'

        # Path specific use case
        if 'path__starts' in params:
            path = params.pop('path__starts')
            path = '/' + path.strip('/')
        else:
            path = get_content_path(self.context)

        if '_size' in params:
            size = params.pop('_size')

        wheres = []
        arguments = []
        selects = []
        selects_arguments = []
        for field, value in params.items():
            result = process_queried_field(field, value)
            if result is None:
                continue
            sql, value, select = result
            wheres.append(sql)
            arguments.append(value)
            if select is not None:
                selects.append(select)
                selects_arguments.append(value)

        return ParsedQueryInfo(
            from_=from_,
            size=size,
            wheres=wheres,
            wheres_arguments=arguments,
            selects=selects,
            selects_arguments=selects_arguments,
            sort_on=sort_field,
            sort_dir=sort_dir,
            full_objects=full_objects
        )


class BasicJsonIndex:
    operators: typing.List[str] = ['=', '!=', '?', '?|']

    def __init__(self, name):
        self.name = name

    @property
    def idx_name(self):
        return 'idx_objects_{}'.format(self.name)

    @property
    def index_sql(self):
        return [
            f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name}
                ON objects ((json->>'{self.name}'));''',
            f'''CREATE INDEX CONCURRENTLY IF NOT EXISTS {self.idx_name}
                ON objects USING gin ((json->'{self.name}'))'''
        ]

    def where(self, value, operator='='):
        assert operator in self.operators
        if operator in ('?', '?|'):
            return f"""json->'{self.name}' {operator} ${{arg}} """
        else:
            return f"""json->>'{self.name}' {operator} ${{arg}} """

    def order_by(self, direction='ASC'):
        return f"order by json->>'{self.name}' {direction}"

    def select(self):
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
        """
        assert not operator
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
        sort_on = query.sort_on
        if sort_on is None:
            # always need a sort otherwise paging never works
            order_by_index = get_pg_index('uuid')
        else:
            order_by_index = get_pg_index(query.sort_on) or BasicJsonIndex(query.sort_on)

        sql_arguments = []
        sql_wheres = []
        select_fields = ['id', 'zoid', 'json']
        arg_index = 1
        for idx, select in enumerate(query.selects):
            select_fields.append(select.format(arg=arg_index))
            sql_arguments.append(query.selects_arguments[idx])
            arg_index += 1

        for idx, where in enumerate(query.wheres):
            sql_wheres.append(where.format(arg=arg_index))
            sql_arguments.append(query.wheres_arguments[idx])
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
            clear_table_name(txn.storage._objects_table_name),
            ' AND '.join(sql_wheres),
            order_by_index.order_by(query.sort_dir),
            query.size,
            query.from_
        )
        return sql, sql_arguments

    def build_count_query(self, context,
                          query: ParsedQueryInfo) -> typing.Tuple[str, typing.List[typing.Any]]:
        sql_arguments = []
        sql_wheres = []
        select_fields = ['count(*)']
        arg_index = 1
        for idx, where in enumerate(query.wheres):
            sql_wheres.append(where.format(arg=arg_index))
            sql_arguments.append(query.wheres_arguments[idx])
            arg_index += 1

        sql_wheres.extend(self.get_default_where_clauses(context))

        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        sql = '''select {}
                 from {}
                 where {}'''.format(
            ','.join(select_fields),
            clear_table_name(txn.storage._objects_table_name),
            ' AND '.join(sql_wheres))
        return sql, sql_arguments

    async def search(self, context, query: ParsedQueryInfo):  # type: ignore
        sql, arguments = self.build_query(context, query)
        txn = get_transaction()
        if txn is None:
            raise TransactionNotFound()
        conn = await txn.get_connection()

        results = []
        context_url = get_object_url(context)
        logger.debug(f'Running search:\n{sql}\n{arguments}')
        for record in await conn.fetch(sql, *arguments):
            data = json.loads(record['json'])
            data['@name'] = record['id']
            data['@uid'] = record['zoid']
            data['@id'] = data['@absolute_url'] = context_url + data['path']
            results.append(data)

        # also do count...
        sql, arguments = self.build_count_query(context, query)
        logger.debug(f'Running search:\n{sql}\n{arguments}')
        records = await conn.fetch(sql, *arguments)
        return {
            'member': results,
            'total': records[0]['count']
        }

    async def index(self, container, datas):
        pass

    async def remove(self, container, uids):
        pass

    async def reindex_all_content(self, container, security=False):
        """
        recursively go through all content to reindex jsonb...
        """
