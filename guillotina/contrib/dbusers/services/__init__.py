from . import groups  # noqa
from . import users  # noqa
from guillotina import configure
from guillotina.api.content import DefaultPOST
from guillotina.contrib.dbusers.content.groups import IGroupManager
from guillotina.contrib.dbusers.content.users import IUserManager


# override some views...
configure.service(context=IGroupManager, method="POST", permission="guillotina.AddGroup", allow_access=True)(
    DefaultPOST
)


@configure.service(context=IUserManager, method="POST", permission="guillotina.AddUser", allow_access=True)
class UserPOST(DefaultPOST):
    async def get_data(self):
        data = await super().get_data()
        if "username" in data:
            data["id"] = data["username"]
        elif "id" in data:
            data["username"] = data["id"]
        return data
