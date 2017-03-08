def make_binary(x):
    if isinstance(x, bytes):
        return x
    return x.encode('ascii')


def non_native_string(x):
    if isinstance(x, bytes):
        return x
    return bytes(x, 'unicode_escape')
