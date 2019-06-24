from guillotina import configure
from guillotina.auth.validators import hash_password
from guillotina.contrib.dbusers.content.groups import IGroup
from guillotina.contrib.dbusers.content.users import IUser
from guillotina.event import notify
from guillotina.events import NewUserAdded
from guillotina.exceptions import PreconditionFailed
from guillotina.interfaces import IObjectAddedEvent
from guillotina.interfaces import IObjectModifiedEvent
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to


@configure.subscriber(for_=(IUser, IObjectAddedEvent))
async def user_created(user, event):
    user.password = hash_password(user.password)

    # user has access to his own object by default
    container = get_current_container()
    roleperm = IPrincipalRoleManager(container)
    roleperm.assign_role_to_principal("guillotina.Owner", user.id)

    await notify(NewUserAdded(user))


@configure.subscriber(for_=(IGroup, IObjectModifiedEvent))
async def update_groups(group, event):
    container = get_current_container()
    users = group.users
    for user in users:
        try:
            context = await navigate_to(container, f"users/{user}")
        except KeyError:
            raise PreconditionFailed(container, "inexistent user")

        if group.id not in context.user_groups:
            context.user_groups.append(user)
            context.register()
