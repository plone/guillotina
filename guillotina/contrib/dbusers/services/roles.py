from guillotina import configure
from guillotina.api.service import Service
from guillotina.auth.role import global_roles
from guillotina.interfaces import IContainer


@configure.service(
    context=IContainer,
    name="@available-roles",
    permission="guillotina.ManageUsers",
    summary="Get available roles on guillotina container",
    method="GET"
)
class AvailableRoles(Service):
    async def __call__(self):
        roles = global_roles()
        return roles
