from plone.server import app_settings
from plone.server.utils import resolve_or_get


async def authenticate_request(request):
    for policy in app_settings['auth_extractors']:
        policy = resolve_or_get(policy)
        token = await policy(request).extract_token()
        if token:
            for validator in app_settings['auth_token_validators']:
                validator = resolve_or_get(validator)
                user = await validator(request).validate(token)
                if user:
                    return user


async def find_user(request, token):
    for identifier in app_settings['auth_user_identifiers']:
        identifier = resolve_or_get(identifier)
        user = await identifier(request).get_user(token)
        if user:
            return user
