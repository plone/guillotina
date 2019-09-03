from copy import deepcopy
from guillotina.schema.interfaces import IContextAwareDefaultFactory


def make_binary(x):
    if isinstance(x, bytes):
        return x
    return x.encode("ascii")


def non_native_string(x):
    if isinstance(x, bytes):
        return x
    return bytes(x, "unicode_escape")


def get_default_from_schema(context, schema, fieldname, default=None):
    """helper to lookup default value of a field
    """
    if schema is None:
        return default
    field = schema.get(fieldname, None)
    if field is None:
        return default
    df = getattr(field, "defaultFactory", None)
    if df is not None:
        if IContextAwareDefaultFactory.providedBy(df):
            return deepcopy(field.defaultFactory(context))
        else:
            return deepcopy(field.defaultFactory())
    if field.default is not None:
        return deepcopy(field.default)
    if field.default != default:
        return field.default
    return default
