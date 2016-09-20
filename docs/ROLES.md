# Requests security

By default request has participation of anonymous user plus the ones added by auth pluggins

# Databases, Application and static files objects

Databases and static files has an specific permission system. They don't have roles by default
and the permissions are specified to RootUser

 * plone.AddPortal
 * plone.GetPortals
 * plone.DeletePortals
 * plone.AccessContent
 * plone.GetDatabases

Anonymous user has on DB/StaticFiles/StaticDirectories/Application object :

 * plone.AccessContent

# Roles in plone.server Site objects

Defined at:

 * plone/plone.server/src/plone.server/plone/server/permissions.zcml
 * plone/plone.server/src/plone.server/plone/server/security.zcml

## Content Related

### plone.Anonymous

 * plone.AccessPreflight

### plone.Member

 * plone.AccessContent

### plone.Reader

 * plone.AccessContent
 * plone.ViewContent

### plone.Editor

 * plone.ModifyContent

### plone.Reviewer

### plone.Owner

 * plone.AccessContent
 * plone.ViewContent
 * plone.ModifyContent
 * plone.DeleteContent
 * plone.AddContent
 * plone.ChangePermissions
 * plone.SeePermissions

## Global Roles

### plone.SiteAdmin

 * plone.RegisterConfigurations
 * plone.WriteConfiguration
 * plone.ReadConfiguration

### plone.SiteDeleter

 * plone.DeletePortal

### plone.Manager

 * plone.ManageAddons


# Default roles on Plone Site

They are stored in anontations using IRolePermissionMap.

Created objects set the plone.Owner role to the user who created it.

# Default groups on Plone Site

## Managers

Has all the permissions of the site