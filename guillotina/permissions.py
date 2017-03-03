from guillotina import configure


configure.permission('guillotina.AccessContent', 'Access content')
configure.permission('guillotina.ModifyContent', 'Modify content')
configure.permission('guillotina.DeleteContent', 'Delete content')
configure.permission('guillotina.AddContent', 'Add content')
configure.permission('guillotina.ViewContent', 'View content')

configure.permission('guillotina.AddPortal', 'Add a portal/DB')
configure.permission('guillotina.GetPortals', 'Get a portal/DB')
configure.permission('guillotina.DeletePortals', 'Delete a portal')

configure.permission('guillotina.MountDatabase', 'Mount a Database')
configure.permission('guillotina.GetDatabases', 'Get Databases')
configure.permission('guillotina.UmountDatabase', 'Umount a Database')

configure.permission('guillotina.AccessPreflight', 'Access Preflight View')

configure.permission('guillotina.ReadConfiguration', 'Read a configuration')
configure.permission('guillotina.WriteConfiguration', 'Write a configuration')
configure.permission('guillotina.RegisterConfigurations',
                     'Register a new configuration on Registry')

configure.permission('guillotina.ManageAddons', 'Manage addons on a site')

configure.permission('guillotina.SeePermissions', 'See permissions')
configure.permission('guillotina.ChangePermissions', 'Change permissions')

configure.permission('guillotina.SearchContent', 'Search content')
configure.permission('guillotina.RawSearchContent', 'Raw search content')
configure.permission('guillotina.ReindexContent', 'Reindex Content')
configure.permission('guillotina.ManageCatalog', 'Manage catalog')

configure.permission('guillotina.GetAPIDefinition', 'Get the API definition')


configure.role("guillotina.Anonymous", "Everybody",
               "All users have this role implicitly", False)
configure.role("guillotina.Authenticated", "Authenticated user",
               "Role automatically assigned to authenticated users", False)
configure.role("guillotina.Member", "Site Member", False)

configure.role("guillotina.Reader", "Reader", "can read content", True)
configure.role("guillotina.Editor", "Editor", "can edit content", True)
configure.role("guillotina.Reviewer", "Reviewer", "can review content", True)
configure.role("guillotina.Owner", "Content Manager",
               "can add/delete content", True)

configure.role("guillotina.Manager", "Site Manager", False)
configure.role("guillotina.SiteAdmin", "Site Administrator",
               "can set settings on site", False)
configure.role("guillotina.SiteCreator", "Site DB Manager",
               "Can create sites and db connections", False)
configure.role("guillotina.SiteDeleter", "Site Remover", "Can destroy a site", False)


# Anonymous
configure.grant(
    permission="guillotina.AccessPreflight",
    role="guillotina.Anonymous")

# Reader
configure.grant(
    permission="guillotina.ViewContent",
    role="guillotina.Reader")
configure.grant(
    permission="guillotina.AccessContent",
    role="guillotina.Reader")

# Reviewer
configure.grant(
    permission="guillotina.ViewContent",
    role="guillotina.Reviewer")
configure.grant(
    permission="guillotina.AccessContent",
    role="guillotina.Reviewer")

# Owner
configure.grant(
    permission="guillotina.DeleteContent",
    role="guillotina.Owner")
configure.grant(
    permission="guillotina.AddContent",
    role="guillotina.Owner")
configure.grant(
    permission="guillotina.AccessContent",
    role="guillotina.Owner")
configure.grant(
    permission="guillotina.ViewContent",
    role="guillotina.Owner")
configure.grant(
    permission="guillotina.ModifyContent",
    role="guillotina.Owner")
configure.grant(
    permission="guillotina.ChangePermissions",
    role="guillotina.Owner")

configure.grant(
    permission="guillotina.SeePermissions",
    role="guillotina.Owner")
configure.grant(
    permission="guillotina.ReindexContent",
    role="guillotina.Owner")

#  Editor
configure.grant(
    permission="guillotina.ViewContent",
    role="guillotina.Editor")
configure.grant(
    permission="guillotina.AccessContent",
    role="guillotina.Editor")
configure.grant(
    permission="guillotina.ModifyContent",
    role="guillotina.Editor")
configure.grant(
    permission="guillotina.ReindexContent",
    role="guillotina.Editor")

# SiteAdmin
configure.grant(
    permission="guillotina.AccessContent",
    role="guillotina.SiteAdmin")
configure.grant(
    permission="guillotina.ManageAddons",
    role="guillotina.SiteAdmin")
configure.grant(
    permission="guillotina.ReadConfiguration",
    role="guillotina.SiteAdmin")
configure.grant(
    permission="guillotina.WriteConfiguration",
    role="guillotina.SiteAdmin")
configure.grant(
    permission="guillotina.RegisterConfigurations",
    role="guillotina.SiteAdmin")
configure.grant(
    permission="guillotina.ManageCatalog",
    role="guillotina.SiteAdmin")
configure.grant(
    permission="guillotina.RawSearchContent",
    role="guillotina.SiteAdmin")

# SiteDeleter
configure.grant(
    permission="guillotina.DeletePortals",
    role="guillotina.SiteDeleter")

# Member
configure.grant(
    permission="guillotina.SearchContent",
    role="guillotina.Member")
