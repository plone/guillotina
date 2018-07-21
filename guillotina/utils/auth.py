from guillotina.interfaces import IPrincipal
from guillotina.interfaces import IRequest
from typing import Optional


def get_authenticated_user(request: IRequest) -> Optional[IPrincipal]:
    """
    Get the currently authenticated user

    :param request: request the user is authenticated against
    """
    if (hasattr(request, 'security') and
            hasattr(request.security, 'participations') and
            len(request.security.participations) > 0):
        return request.security.participations[0].principal
    else:
        return None


def get_authenticated_user_id(request: IRequest) -> Optional[str]:
    """
    Get the currently authenticated user id

    :param request: request the user is authenticated against
    """
    user = get_authenticated_user(request)
    if user:
        return user.id
    return None
