from typing import Optional

from guillotina import task_vars
from guillotina.component import get_adapter
from guillotina.interfaces import IPrincipal
from guillotina.interfaces import ISecurityPolicy


def get_authenticated_user() -> Optional[IPrincipal]:
    """
    Get the currently authenticated user

    :param request: request the user is authenticated against
    """
    return task_vars.authenticated_user.get()


def get_authenticated_user_id() -> Optional[str]:
    """
    Get the currently authenticated user id

    :param request: request the user is authenticated against
    """
    user = get_authenticated_user()
    if user:
        return user.id
    return None


def get_security_policy(user: Optional[IPrincipal] = None) -> ISecurityPolicy:
    if user is None:
        user = get_authenticated_user()
        if user is None:
            from guillotina.auth.users import AnonymousUser
            user = AnonymousUser()
    security_policies = task_vars.security_policies.get()
    if security_policies is None:
        security_policies = {}
        task_vars.security_policies.set(security_policies)
    if user.id not in security_policies:
        security_policies[user.id] = get_adapter(user, ISecurityPolicy)
    return security_policies[user.id]
