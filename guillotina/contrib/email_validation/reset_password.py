from guillotina.auth.utils import find_user


async def run(token_data, payload):
    user_to_change_password = token_data['v_user']
    user = await find_user({
        'id': user_to_change_password
    })

    await user.set_password(
        payload.get('password', None)
    )
