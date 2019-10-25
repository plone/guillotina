from .content.groups import Group
from .content.users import User
from guillotina import configure
from guillotina.auth.validators import hash_password
from guillotina.contrib.dbusers.content.groups import IGroup
from guillotina.contrib.dbusers.content.users import IUser
from guillotina.event import notify
from guillotina.events import NewUserAdded
from guillotina.events import ObjectAddedEvent
from guillotina.events import ObjectModifiedEvent
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.response import HTTPPreconditionFailed
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to


@configure.subscriber(for_=(IUser, IObjectAddedEvent))
async def on_user_created(user: User, event: ObjectAddedEvent) -> None:
    # Store only the hash of the password
    user.password = hash_password(user.password)

    # Give user ownership to his own folder object by default
    roleperm = IPrincipalRoleManager(user)
    roleperm.assign_role_to_principal("guillotina.Owner", user.id)

    await notify(NewUserAdded(user))


@configure.subscriber(for_=(IGroup, IObjectModifiedEvent))
async def on_update_groups(group: Group, event: ObjectModifiedEvent) -> None:
    # Keep group.users and user.user_groups in sync
    container = get_current_container()
    users = group.users or []
    for user_id in users:
        try:
            # Get the user
            user = await navigate_to(container, f"users/{user_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent user: {user_id}"})

        # Add group to user groups field
        if group.id not in user.user_groups:
            user.user_groups.append(group.id)
            user.register()
