from guillotina import app_settings
from guillotina.auth import authenticate_user
from guillotina.content import create_content_in_container
from guillotina.event import notify
from guillotina.events import ObjectAddedEvent
from guillotina.events import UserLogin
from guillotina.utils import get_current_container


async def run(token_data, payload):
    # Payload : {
    #   'new_password': 'secret',
    # }
    container = get_current_container()
    user_folders = await container.async_get("users")

    data = {}

    valid_data = ["username", "email", "name", "password", "properties"]

    for key in valid_data:
        if key in token_data:
            data[key] = token_data[key]

    user = await create_content_in_container(
        user_folders,
        "User",
        token_data.get("username", token_data.get("id")),
        creators=(token_data.get("username", token_data.get("id")),),
        check_security=False,
        **data,
    )
    user.user_roles = ["guillotina.Member"]
    await notify(ObjectAddedEvent(user))

    jwt_token, data = authenticate_user(user.id, timeout=app_settings["jwt"]["token_expiration"])
    await notify(UserLogin(user, jwt_token))

    return {"exp": data["exp"], "token": jwt_token}
