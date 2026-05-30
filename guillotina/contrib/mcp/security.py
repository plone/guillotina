from typing import Any

from guillotina.response import HTTPUnauthorized
from guillotina.utils import get_roles_principal, get_security_policy


def has_permission(permission: str, context: Any) -> bool:
    return bool(get_security_policy().check_permission(permission, context))


def require_permission(permission: str, context: Any) -> None:
    if not has_permission(permission, context):
        raise HTTPUnauthorized(content={"reason": f"Missing permission: {permission}"})


def require_access_content(context: Any) -> None:
    require_permission("guillotina.AccessContent", context)


def require_view_content(context: Any) -> None:
    require_permission("guillotina.ViewContent", context)


def has_manager_role(context: Any) -> bool:
    return "guillotina.Manager" in get_roles_principal(context)
