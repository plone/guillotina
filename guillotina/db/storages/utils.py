

def get_table_definition(name, schema, primary_keys=[]):
    pk = ''
    if len(primary_keys) > 0:
        pk = ', CONSTRAINT pk_{} PRIMARY KEY({})'.format(name, ', '.join(primary_keys))
    return "CREATE TABLE IF NOT EXISTS {} ({}{});".format(
        name,
        ',\n'.join('{} {}'.format(c, d) for c, d in schema.items()),
        pk
    )


_statements = {}

def register_sql(name, sql):
    _statements[name] = sql


class SQLStatements:

    def __init__(self):
        self._cached = {}

    def get(self, name, table_name):
        if name in self._cached:
            return self._cached[name]
        sql = _statements[name].format(table_name=table_name)
        self._cached[name] = sql
        return sql
