from typing import Optional

from guillotina import task_vars
from guillotina.interfaces import IPrincipal


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
