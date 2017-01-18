from plone.server import configure


configure.permission('plone.AccessContent', 'Access content')
configure.permission('plone.ModifyContent', 'Modify content')
configure.permission('plone.DeleteContent', 'Delete content')
configure.permission('plone.AddContent', 'Add content')
configure.permission('plone.ViewContent', 'View content')

configure.permission('plone.AddPortal', 'Add a portal/DB')
configure.permission('plone.GetPortals', 'Get a portal/DB')
configure.permission('plone.DeletePortals', 'Delete a portal')

configure.permission('plone.MountDatabase', 'Mount a Database')
configure.permission('plone.GetDatabases', 'Get Databases')
configure.permission('plone.UmountDatabase', 'Umount a Database')

configure.permission('plone.AccessPreflight', 'Access Preflight View')

configure.permission('plone.ReadConfiguration', 'Read a configuration')
configure.permission('plone.WriteConfiguration', 'Write a configuration')
configure.permission('plone.RegisterConfigurations', 'Register a new configuration on Registry')

configure.permission('plone.ManageAddons', 'Manage addons on a site')

configure.permission('plone.SeePermissions', 'See permissions')
configure.permission('plone.ChangePermissions', 'Change permissions')

configure.permission('plone.SearchContent', 'Search content')
configure.permission('plone.RawSearchContent', 'Raw search content')
configure.permission('plone.ReindexContent', 'Reindex Content')
configure.permission('plone.ManageCatalog', 'Manage catalog')

configure.permission('plone.GetAPIDefinition', 'Get the API definition')


configure.role("plone.Anonymous", "Everybody", "All users have this role implicitly")
configure.role("plone.Authenticated", "Authenticated user", "Role automatically assigned to authenticated users")  # noqa
configure.role("plone.Member", "Site Member")

configure.role("plone.Reader", "Reader", "can read content")
configure.role("plone.Editor", "Editor", "can edit content")
configure.role("plone.Reviewer", "Reviewer", "can review content")
configure.role("plone.Owner", "Content Manager", "can add/delete content")

configure.role("plone.Manager", "Site Manager")
configure.role("plone.SiteAdmin", "Site Administrator", "can set settings on site")
configure.role("plone.SiteCreator", "Site DB Manager", "Can create sites and db connections")
configure.role("plone.SiteDeleter", "Site Remover", "Can destroy a site")


# Anonymous
configure.grant(
    permission="plone.AccessPreflight",
    role="plone.Anonymous")

# Reader
configure.grant(
    permission="plone.ViewContent",
    role="plone.Reader")
configure.grant(
    permission="plone.AccessContent",
    role="plone.Reader")

# Owner
configure.grant(
    permission="plone.DeleteContent",
    role="plone.Owner")
configure.grant(
    permission="plone.AddContent",
    role="plone.Owner")
configure.grant(
    permission="plone.AccessContent",
    role="plone.Owner")
configure.grant(
    permission="plone.ViewContent",
    role="plone.Owner")
configure.grant(
    permission="plone.ModifyContent",
    role="plone.Owner")
configure.grant(
    permission="plone.ChangePermissions",
    role="plone.Owner")

configure.grant(
    permission="plone.SearchContent",
    role="plone.Member")
configure.grant(
    permission="plone.RawSearchContent",
    role="plone.SiteAdmin")

configure.grant(
    permission="plone.SeePermissions",
    role="plone.Owner")
configure.grant(
    permission="plone.ReindexContent",
    role="plone.Owner")

#  Editor
configure.grant(
    permission="plone.ViewContent",
    role="plone.Editor")
configure.grant(
    permission="plone.AccessContent",
    role="plone.Editor")
configure.grant(
    permission="plone.ModifyContent",
    role="plone.Editor")
configure.grant(
    permission="plone.ReindexContent",
    role="plone.Editor")

# SiteAdmin
configure.grant(
    permission="plone.AccessContent",
    role="plone.SiteAdmin")
configure.grant(
    permission="plone.ManageAddons",
    role="plone.SiteAdmin")
configure.grant(
    permission="plone.ReadConfiguration",
    role="plone.SiteAdmin")
configure.grant(
      permission="plone.WriteConfiguration",
      role="plone.SiteAdmin")
configure.grant(
    permission="plone.RegisterConfigurations",
    role="plone.SiteAdmin")
configure.grant(
    permission="plone.ManageCatalog",
    role="plone.SiteAdmin")

# SiteDeleter
configure.grant(
    permission="plone.DeletePortals",
    role="plone.SiteDeleter")
