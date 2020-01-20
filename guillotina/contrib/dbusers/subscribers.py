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
from guillotina.interfaces import IBeforeObjectAddedEvent
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


@configure.subscriber(for_=(IUser, IObjectAddedEvent))
async def on_user_added(user: User, event) -> None:
    await _update_groups(user.id, user.groups, [])


@configure.subscriber(for_=(IUser, IBeforeObjectRemovedEvent))
async def on_user_removed(user: User, event) -> None:
    await _update_groups(user.id, [], user.groups)


@configure.subscriber(for_=(IUser, IBeforeObjectModifiedEvent))
async def on_user_modified(user: User, event: BeforeObjectModifiedEvent) -> None:
    # keep group.users updated with changes from users
    old_groups = user.user_groups or []
    new_groups = event.payload.get("user_groups", [])
    groups_added = set(new_groups) - set(old_groups)
    groups_removed = set(old_groups) - set(new_groups)
    await _update_groups(user.id, groups_added, groups_removed)


@configure.subscriber(for_=(IGroup, IObjectAddedEvent))
async def on_group_added(group: Group, event: ObjectAddedEvent) -> None:
    await _update_users(group.id, group.users, [])


@configure.subscriber(for_=(IGroup, IBeforeObjectRemovedEvent))
async def on_group_removed(group: Group, event: ObjectAddedEvent) -> None:
    await _update_users(group.id, [], group.users)


@configure.subscriber(for_=(IGroup, IBeforeObjectModifiedEvent))
async def on_group_modified(group: Group, event: BeforeObjectModifiedEvent) -> None:
    # keep group.users updated with changes from users
    old_users = group.users or []
    users_added = set() - set(old_users)
    users_removed = set(old_users) - set()
    changes = event.payload.get("users", {})
    for user, is_new in changes.items():
        if is_new:
            users_added.add(user)
        else:
            users_removed.add(user)
    await _update_users(group.id, users_added, users_removed)


async def _update_groups(user_id, groups_added, groups_removed):
    container = get_current_container()
    for group_id in groups_added:
        try:
            group: Group = await navigate_to(container, f"groups/{group_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent group: {group_id}"})
        if user_id not in group.users:
            group.users.append(user_id)
            group.register()

    for group_id in groups_removed:
        try:
            group: Group = await navigate_to(container, f"groups/{group_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent group: {group_id}"})
        if user_id in group.users:
            group.users.remove(user_id)
            group.register()


async def _update_users(group_id, users_added, users_removed):
    container = get_current_container()
    for user_id in users_added:
        try:
            user: User = await navigate_to(container, f"users/{user_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent user: {user_id}"})
        if group_id not in user.groups:
            user.user_groups.append(group_id)
            user.register()

    for user_id in users_removed:
        try:
            user: User = await navigate_to(container, f"users/{user_id}")
        except KeyError:
            raise HTTPPreconditionFailed(content={"reason": f"inexistent user: {user_id}"})
        if group_id in user.groups:
            user.user_groups.remove(group_id)
            user.register()
