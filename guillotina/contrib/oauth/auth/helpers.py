from guillotina import app_settings
from guillotina.auth.utils import set_authenticated_user


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
