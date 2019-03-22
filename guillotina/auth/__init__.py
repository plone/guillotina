from datetime import datetime
from datetime import timedelta

import jwt
from guillotina._settings import app_settings
from guillotina.auth import groups  # noqa
from guillotina.auth.users import ROOT_USER_ID
from guillotina.profile import profilable


@profilable
async def authenticate_request(request):
    for policy in app_settings['auth_extractors']:
        token = await policy(request).extract_token()
        if token:
            for validator in app_settings['auth_token_validators']:
                if (validator.for_validators is not None and
                        policy.name not in validator.for_validators):
                    continue
                user = await validator(request).validate(token)
                if user is not None:
                    return user


@profilable
async def find_user(request, token):
    if token.get('id') == ROOT_USER_ID:
        return request.application.root_user
    for identifier in app_settings['auth_user_identifiers']:
        user = await identifier(request).get_user(token)
        if user is not None:
            return user


def authenticate_user(userid, data=None, timeout=60 * 60 * 1):
    if data is None:
        data = {}
    data.update({
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(seconds=timeout),
        'id': userid
    })
    jwt_token = jwt.encode(
        data, app_settings['jwt']['secret'],
        algorithm=app_settings['jwt']['algorithm']).decode('utf-8')
    return jwt_token, data
