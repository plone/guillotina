from guillotina import configure


configure.permission("guillotina.AccessContent", "Access content")
configure.permission("guillotina.ModifyContent", "Modify content")
configure.permission("guillotina.DeleteContent", "Delete content")
configure.permission("guillotina.AddContent", "Add content")
configure.permission("guillotina.MoveContent", "Move content")
configure.permission("guillotina.DuplicateContent", "Duplicate content")
configure.permission("guillotina.ViewContent", "View content")

configure.permission("guillotina.AddContainer", "Add a portal/DB")
configure.permission("guillotina.GetContainers", "Get a portal/DB")
configure.permission("guillotina.DeleteContainers", "Delete a portal")

configure.permission("guillotina.MountDatabase", "Mount a Database")
configure.permission("guillotina.GetDatabases", "Get Databases")
configure.permission("guillotina.UmountDatabase", "Umount a Database")

configure.permission("guillotina.AccessPreflight", "Access Preflight View")

configure.permission("guillotina.ReadConfiguration", "Read a configuration")
configure.permission("guillotina.WriteConfiguration", "Write a configuration")
configure.permission("guillotina.RegisterConfigurations", "Register a new configuration on Registry")

configure.permission("guillotina.ManageAddons", "Manage addons on a container")

configure.permission("guillotina.SeePermissions", "See permissions")
configure.permission("guillotina.ChangePermissions", "Change permissions")

configure.permission("guillotina.RefreshToken", "Refresh token")

configure.permission("guillotina.SearchContent", "Search content")
configure.permission("guillotina.RawSearchContent", "Raw search content")
configure.permission("guillotina.ReindexContent", "Reindex Content")
configure.permission("guillotina.ManageCatalog", "Manage catalog")

configure.permission("guillotina.GetAPIDefinition", "Get the API definition")
configure.permission("guillotina.Public", "Public access to content")
configure.permission("guillotina.WebSocket", "Access to websocket")

configure.permission("guillotina.CacheManage", "Manage cache")

configure.role("guillotina.Anonymous", "Everybody", "All users have this role implicitly", False)
configure.role(
    "guillotina.Authenticated",
    "Authenticated user",
    "Role automatically assigned to authenticated users",
    False,
)
configure.role("guillotina.Member", "Member", False)

configure.role("guillotina.Reader", "Reader", "can read content", True)
configure.role("guillotina.Editor", "Editor", "can edit content", True)
configure.role("guillotina.Reviewer", "Reviewer", "can review content", True)
configure.role("guillotina.Owner", "Content Manager", "can add/delete content", True)

configure.role("guillotina.Manager", "Container Manager", False)
configure.role("guillotina.ContainerAdmin", "Container Administrator", "can set settings on container", False)
configure.role(
    "guillotina.ContainerCreator", "Container DB Manager", "Can create containers and db connections", False
)
configure.role("guillotina.ContainerDeleter", "Container Remover", "Can destroy a container", False)


# Anonymous
configure.grant(permission="guillotina.AccessPreflight", role="guillotina.Anonymous")
configure.grant(permission="guillotina.Public", role="guillotina.Anonymous")

# Authenticated
configure.grant(permission="guillotina.RefreshToken", role="guillotina.Authenticated")
configure.grant(permission="guillotina.AccessPreflight", role="guillotina.Authenticated")
configure.grant(permission="guillotina.Public", role="guillotina.Authenticated")

configure.grant(permission="guillotina.UseWebSockets", role="guillotina.Authenticated")

# Reader
configure.grant(permission="guillotina.ViewContent", role="guillotina.Reader")
configure.grant(permission="guillotina.AccessContent", role="guillotina.Reader")
configure.grant(permission="guillotina.DuplicateContent", role="guillotina.Reader")

# Reviewer
configure.grant(permission="guillotina.ViewContent", role="guillotina.Reviewer")
configure.grant(permission="guillotina.AccessContent", role="guillotina.Reviewer")

# Owner
configure.grant(permission="guillotina.DeleteContent", role="guillotina.Owner")
configure.grant(permission="guillotina.AddContent", role="guillotina.Owner")
configure.grant(permission="guillotina.MoveContent", role="guillotina.Owner")
configure.grant(permission="guillotina.DuplicateContent", role="guillotina.Owner")
configure.grant(permission="guillotina.AccessContent", role="guillotina.Owner")
configure.grant(permission="guillotina.ViewContent", role="guillotina.Owner")
configure.grant(permission="guillotina.ModifyContent", role="guillotina.Owner")
configure.grant(permission="guillotina.ChangePermissions", role="guillotina.Owner")

configure.grant(permission="guillotina.SeePermissions", role="guillotina.Owner")
configure.grant(permission="guillotina.ReindexContent", role="guillotina.Owner")

#  Editor
configure.grant(permission="guillotina.ViewContent", role="guillotina.Editor")
configure.grant(permission="guillotina.AccessContent", role="guillotina.Editor")
configure.grant(permission="guillotina.ModifyContent", role="guillotina.Editor")
configure.grant(permission="guillotina.MoveContent", role="guillotina.Editor")
configure.grant(permission="guillotina.DuplicateContent", role="guillotina.Editor")
configure.grant(permission="guillotina.ReindexContent", role="guillotina.Editor")

# ContainerAdmin
configure.grant(permission="guillotina.AccessContent", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.ManageAddons", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.ReadConfiguration", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.WriteConfiguration", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.RegisterConfigurations", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.ManageCatalog", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.RawSearchContent", role="guillotina.ContainerAdmin")
configure.grant(permission="guillotina.CacheManage", role="guillotina.Manager")
configure.grant(permission="guillotina.Manage", role="guillotina.Manager")

# ContainerDeleter
configure.grant(permission="guillotina.DeleteContainers", role="guillotina.ContainerDeleter")

# Member
configure.grant(permission="guillotina.SearchContent", role="guillotina.Member")
