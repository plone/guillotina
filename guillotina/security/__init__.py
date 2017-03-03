_view_permissions = {}


def protect_view(cls, permission):
    _view_permissions[cls] = permission


def get_view_permission(cls):
    return _view_permissions.get(cls, None)
