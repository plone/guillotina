from plone.server import app_settings
from plone.server.utils import resolve_or_get


async def authenticate_request(request):
    for policy in app_settings['auth_policies']:
        policy = resolve_or_get(policy)
        token = await policy(request).extract_token()
        if token:
            user = await find_user(request, token)
            if user:
                if await authenticate_user(request, user, token):
                    return user


async def find_user(request, token):
    for identifier in app_settings['auth_user_identifiers']:
        identifier = resolve_or_get(identifier)
        user = await identifier(request).get_user()
        if user:
            return user


async def authenticate_user(request, user, token):
    for checker in app_settings['auth_token_checker']:
        checker = resolve_or_get(checker)
        if await checker(request).validate(user, token):
            return True
    return False
