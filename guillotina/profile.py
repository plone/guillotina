
_profiled_functions = []


def get_profilable_functions():
    return _profiled_functions


def profilable(func):
    _profiled_functions.append(func)
    return func
