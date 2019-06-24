from guillotina import configure


configure.permission("guillotina.Nobody", "Permission not assigned to anyone")

configure.permission(
    "guillotina.ManageUsers",
    "Manage Users on site",
    "Be able to manage users on site"
)

configure.grant(
    permission="guillotina.ManageUsers",
    role="guillotina.Manager"
)
