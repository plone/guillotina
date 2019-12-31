from .content.groups import Group
from .content.users import User
from guillotina import configure
from guillotina.auth.validators import hash_password
from guillotina.contrib.dbusers.content.groups import IGroup
from guillotina.contrib.dbusers.content.users import IUser
from guillotina.event import notify
from guillotina.events import BeforeObjectModifiedEvent
from guillotina.events import BeforeObjectRemovedEvent
from guillotina.events import NewUserAdded
from guillotina.events import ObjectAddedEvent
from guillotina.events import ObjectModifiedEvent
from guillotina.interfaces import IBeforeObjectModifiedEvent
from guillotina.interfaces import IBeforeObjectRemovedEvent
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


@configure.subscriber(for_=(IUser, BeforeObjectModifiedEvent))
async def on_update_user(user: User, event: ObjectModifiedEvent) -> None:
    # keep group.users updated with changes from users
    old_groups = user.user_groups or []
    new_groups = event.payload.get("user_groups", [])
    groups_added = set(new_groups) - set(old_groups)
    groups_removed = set(old_groups) - set(new_groups)
    container = get_current_container()
    for group_id in groups_added:
        try:
            group = await navigate_to(container, f"groups/{group_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent group: {group_id}"})
        if user.id not in group.users:
            group.users.append(user.id)
            group.register()

    for group_id in groups_removed:
        try:
            group = await navigate_to(container, f"groups/{group_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent group: {group_id}"})
        if user.id in group.users:
            group.users.remove(user.id)
            group.register()


@configure.subscriber(for_=(IUser, BeforeObjectRemovedEvent))
async def on_remove_user(user: User, event: BeforeObjectRemovedEvent):
    container = get_current_container()
    for group_id in user.user_groups:
        group = await navigate_to(container, f"groups/{group_id}")
        group.users.remove(user.id)
        group.register()


@configure.subscriber(for_=(IGroup, BeforeObjectRemovedEvent))
async def on_remove_user(group: Group, event: BeforeObjectRemovedEvent):
    container = get_current_container()
    for user_id in group.users:
        user = await navigate_to(container, f"users/{user_id}")
        user.user_groups.remove(group.id)
        user.register()
