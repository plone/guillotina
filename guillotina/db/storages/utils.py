

def get_table_definition(name, schema, primary_keys=[]):
    pk = ''
    if len(primary_keys) > 0:
        pk = ', PRIMARY KEY({})'.format(', '.join(primary_keys))
    return "CREATE TABLE IF NOT EXISTS {} ({});".format(
        name,
        ',\n'.join('{} {}'.format(c, d) for c, d in schema.items()),
        pk
    )
