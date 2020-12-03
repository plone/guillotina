from guillotina import app_settings
from guillotina.auth import authenticate_user
from guillotina.auth.utils import find_user
from guillotina.event import notify
from guillotina.events import UserLogin


async def run(token_data, payload):
    user_to_change_password = token_data["v_user"]
    user = await find_user({"id": user_to_change_password})

    await user.set_password(payload.get("password", None))

    jwt_token, data = authenticate_user(user.id, timeout=app_settings["jwt"]["token_expiration"])
    await notify(UserLogin(user, jwt_token))

    return {"exp": data["exp"], "token": jwt_token}
