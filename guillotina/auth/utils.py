from datetime import datetime
from datetime import timedelta
from guillotina import task_vars
from guillotina._settings import app_settings
from guillotina.auth import groups  # noqa
from guillotina.auth.users import AnonymousUser
from guillotina.auth.users import ROOT_USER_ID
from guillotina.component import get_utility
from guillotina.interfaces import IApplication
from guillotina.interfaces import IPrincipal
from guillotina.profile import profilable
from guillotina.utils import get_security_policy
from typing import Optional

import jwt


@profilable
async def authenticate_request(request) -> Optional[IPrincipal]:
    for policy in app_settings["auth_extractors"]:
        token = await policy(request).extract_token()
        if token:
            for validator in app_settings["auth_token_validators"]:
                if validator.for_validators is not None and policy.name not in validator.for_validators:
                    continue
                user = await validator().validate(token)
                if user is not None:
                    set_authenticated_user(user)
                    return user
    set_authenticated_user(None)
    return None


def set_authenticated_user(user):
    if user is not None and not isinstance(user, AnonymousUser):
        policy = get_security_policy(user)
        policy.invalidate_cache()
        if hasattr(user, "roles") and "guillotina.Authenticated" not in user.roles:
            user.roles["guillotina.Authenticated"] = 1
    task_vars.authenticated_user.set(user)


@profilable
async def find_user(token):
    if token.get("id") == ROOT_USER_ID:
        root = get_utility(IApplication, name="root")
        return root.root_user
    for identifier in app_settings["auth_user_identifiers"]:
        user = await identifier().get_user(token)
        if user is not None:
            return user


def authenticate_user(userid, data=None, timeout=60 * 60 * 1):
    if data is None:
        data = {}
    data.update(
        {"iat": datetime.utcnow(), "exp": datetime.utcnow() + timedelta(seconds=timeout), "id": userid}
    )
    jwt_token = jwt.encode(
        data, app_settings["jwt"]["secret"], algorithm=app_settings["jwt"]["algorithm"]
    ).decode("utf-8")
    return jwt_token, data
