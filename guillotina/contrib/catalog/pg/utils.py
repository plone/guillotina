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
