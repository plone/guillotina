# Requests security

By default request has participation of anonymous user plus the ones added by auth pluggins

# Databases, Application and static files objects

Databases and static files has an specific permission system. They don't have roles by default
and the permissions are specified to root user

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

 * plone.AccessContent
 * plone.ViewContent
 * plone.ModifyContent
 * plone.ReindexContent

### plone.Reviewer

### plone.Owner

 * plone.AccessContent
 * plone.ViewContent
 * plone.ModifyContent
 * plone.DeleteContent
 * plone.AddContent
 * plone.ChangePermissions
 * plone.SeePermissions
 * plone.ReindexContent

## Site/App Roles

### plone.SiteAdmin

 * plone.AccessContent
 * plone.ManageAddons
 * plone.RegisterConfigurations
 * plone.WriteConfiguration
 * plone.ReadConfiguration

### plone.SiteDeleter

 * plone.DeletePortal

# Default roles on Plone Site

They are stored in anontations using IRolePermissionMap.

Created objects set the plone.Owner role to the user who created it.

# Default groups on Plone Site

## Managers

### RootParticipation

There is a `root` user who has permissions to all site:

DB/APP permissions are defined on factory.py

Plone permissions because belongs to Managers group auth/participation.py
