from guillotina import app_settings
from guillotina.auth import groups  # noqa
from guillotina.auth.users import ROOT_USER_ID
from guillotina.utils import resolve_or_get


async def authenticate_request(request):
    for policy in app_settings['auth_extractors']:
        policy = resolve_or_get(policy)
        token = await policy(request).extract_token()
        if token:
            for validator in app_settings['auth_token_validators']:
                validator = resolve_or_get(validator)
                if (validator.for_validators is not None and
                        policy.name not in validator.for_validators):
                    continue
                user = await validator(request).validate(token)
                if user is not None:
                    return user


async def find_user(request, token):
    if token.get('id') == ROOT_USER_ID:
        return request.application.root_user
    for identifier in app_settings['auth_user_identifiers']:
        identifier = resolve_or_get(identifier)
        user = await identifier(request).get_user(token)
        if user is not None:
            return user
