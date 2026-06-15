from guillotina import app_settings
from guillotina.auth.utils import set_authenticated_user
from guillotina.utils import get_authenticated_user


async def authenticate_user_credentials(username, password):
    """Validate username/password credentials through the configured validators."""
    creds = {"type": "basic", "token": password, "id": username}
    for validator in app_settings["auth_token_validators"]:
        if validator.for_validators is not None and "basic" not in validator.for_validators:
            continue
        user = await validator().validate(creds)
        if user is not None:
            set_authenticated_user(user)
            return user


def current_user_or_none():
    """Return the authenticated user, or None when the request is anonymous."""
    user = get_authenticated_user()
    if user is None or getattr(user, "id", "Anonymous User") == "Anonymous User":
        return None
    return user
