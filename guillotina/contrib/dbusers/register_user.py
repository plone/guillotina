from guillotina.content import create_content_in_container
from guillotina.utils import get_current_container
from guillotina.events import ObjectAddedEvent
from guillotina.event import notify
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
