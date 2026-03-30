from guillotina import configure


configure.permission("guillotina.AddUser", title="Add plone user")
configure.permission("guillotina.AddGroup", title="Add plone group")
configure.permission("guillotina.Nobody", "Permission not assigned to anyone")
configure.permission("guillotina.ManageUsers", "Manage Users on site", "Be able to manage users on site")

configure.grant(permission="guillotina.AddUser", role="guillotina.Manager")
configure.grant(permission="guillotina.AddGroup", role="guillotina.Manager")
configure.grant(permission="guillotina.ManageUsers", role="guillotina.Manager")

configure.grant(permission="guillotina.AddUser", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.AddGroup", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.ManageUsers", role="guillotina.ContainerAdmin")
