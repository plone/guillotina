from guillotina.db import ROOT_ID
from guillotina.db import TRASHED_ID


class _BasicType:

    def __init__(self, sql):
        self.sql = sql

    def __str__(self):
        return self.sql


BIGINT = _BasicType('BIGINT')
BOOLEAN = _BasicType('BOOLEAN')
TEXT = _BasicType('TEXT')
JSONB = _BasicType('JSONB')
BYTEA = _BasicType('BYTEA')
INT = _BasicType('INT')


class VARCHAR:

    def __init__(self, size):
        self.size = size

    def __str__(self):
        return 'VARCHAR({})'.format(self.size)


class Column:

    def __init__(self, name, type, not_null=False,
                 references=None, on_delete=None):
        self.name = name
        self.type = type
        self.not_null = not_null
        self.references = references
        self.on_delete = on_delete

    def __str__(self):
        sql = '{} {}'.format(self.name, self.type)
        if self.not_null:
            sql += ' NOT NULL'
        if self.references:
            sql += ' REFERENCES {}'.format(self.references)
        if self.on_delete:
            sql += ' ON DELETE {}'.format(self.on_delete)
        return sql


class Table:

    def __init__(self, name, columns=[], indexes=[]):
        self.name = name
        self.columns = columns
        self.indexes = indexes

    def remove_column(self, name):
        for col in self.columns[:]:
            if name == col.name:
                self.columns.remove(col)
                break

    def add_column(self, column):
        self.columns.append(column)

    def replace_column(self, col):
        self.remove_column(col.name)
        self.add_column(col)

    def drop(self, partition=False):
        if partition is not False:
            table_name = f'{self.name}_{partition}'
        else:
            table_name = self.name
        return f"DROP TABLE IF EXISTS {table_name}"

    def get_statements(self, storage, partition=False):
        columns = ',\n'.join(['    ' + str(c) for c in self.columns])
        if partition is not False:
            table_name = f'{self.name}_{partition}'
            statements = [f"""
CREATE TABLE IF NOT EXISTS {table_name}
PARTITION OF {self.name}
FOR VALUES IN ({partition});
"""]
            statements.extend([i.get_sql(table_name) for i in self.indexes])
        else:
            table_name = self.name
            statement = f"""CREATE TABLE IF NOT EXISTS {self.name} (
{columns}
)
"""
            if storage._partitioning_supported:
                statement += ' PARTITION BY LIST (part)'
            statement += ';'
            statements = [statement]
            if not storage._partitioning_supported:
                statements.extend([i.get_sql(table_name) for i in self.indexes])
        return statements


class Index:

    def __init__(self, name, on_field):
        self.name = name
        self.on_field = on_field

    def get_sql(self, table_name):
        return 'CREATE INDEX IF NOT EXISTS {} ON {} ({});'.format(
            self.name,
            table_name,
            self.on_field
        )


class Sequence:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return 'CREATE SEQUENCE IF NOT EXISTS {};'.format(self.name)


class SQL:

    def __init__(self, sql, default_table='objects'):
        self.sql = sql
        self.default_table = default_table

    def __str__(self):
        return self.render()

    def render(self, storage=None, table=None, ob=None, **kwargs):
        if table is None:
            table = self.default_table
        if (storage is not None and storage._partitioning_supported and
                ob is not None and ob.__part_id__ != 0):
            table += f'_{ob.__part_id__}'
        return self.sql.format(
            table=table,
            trashed_id=TRASHED_ID,
            root_id=ROOT_ID,
            **kwargs
        )
