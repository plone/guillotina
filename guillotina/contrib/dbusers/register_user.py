from guillotina.content import create_content_in_container
from guillotina.utils import get_current_container
from guillotina.events import ObjectAddedEvent
from guillotina.events import UserLogin
from guillotina.event import notify
from guillotina.auth import authenticate_user
from guillotina import app_settings
from copy import deepcopy

async def run(token_data, payload):
    # Payload : {
    #   'new_password': 'secret',
    # }
    container = get_current_container()
    user_folders = await container.async_get('users')

    data = deepcopy(token_data)

    del data['iat']
    del data['exp']

    keys = list(data.keys())
    for key in keys:
        if key.startswith('v_'):
            del data[key]

    user = await create_content_in_container(
        user_folders, "User", token_data['id'], creators=(token_data['id'],), check_security=False, **data
    )
    await notify(ObjectAddedEvent(user))

    jwt_token, data = authenticate_user(user.id, timeout=app_settings["jwt"]["token_expiration"])
    await notify(UserLogin(user, jwt_token))

    return {"exp": data["exp"], "token": jwt_token}