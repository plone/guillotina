# Security

`guillotina` implements robust ACL security.

An overview of our security features are:

* Users are given roles and groups
* Roles are granted permissions
* Groups are granted roles
* Roles can be granted to users on specific objects


## Requests security

By default request has participation of anonymous user plus the ones added by auth pluggins

## Databases, Application and static files objects

Databases and static files has an specific permission system. They don't have roles by default
and the permissions are specified to root user

 * guillotina.AddPortal
 * guillotina.GetPortals
 * guillotina.DeletePortals
 * guillotina.AccessContent
 * guillotina.GetDatabases

Anonymous user has on DB/StaticFiles/StaticDirectories/Application object :

 * guillotina.AccessContent

## Roles in guillotina Site objects

Defined at:

 * guillotina/permissions.py
 * guillotina/security.py

## Content Related

### guillotina.Anonymous

 * guillotina.AccessPreflight

### guillotina.Member

 * guillotina.AccessContent

### guillotina.Reader

 * guillotina.AccessContent
 * guillotina.ViewContent

### guillotina.Editor

 * guillotina.AccessContent
 * guillotina.ViewContent
 * guillotina.ModifyContent
 * guillotina.ReindexContent

### guillotina.Reviewer

### guillotina.Owner

 * guillotina.AccessContent
 * guillotina.ViewContent
 * guillotina.ModifyContent
 * guillotina.DeleteContent
 * guillotina.AddContent
 * guillotina.ChangePermissions
 * guillotina.SeePermissions
 * guillotina.ReindexContent

## Site/App Roles

### guillotina.SiteAdmin

 * guillotina.AccessContent
 * guillotina.ManageAddons
 * guillotina.RegisterConfigurations
 * guillotina.WriteConfiguration
 * guillotina.ReadConfiguration
 * guillotina.ManageCatalog

### guillotina.SiteDeleter

 * guillotina.DeletePortal

## Default roles on Guillotina Site

They are stored in anontations using IRolePermissionMap.

Created objects set the guillotina.Owner role to the user who created it.

## Default groups on Guillotina Site

### Managers

#### RootParticipation

There is a `root` user who has permissions to all site:

DB/APP permissions are defined on factory.py

Guillotina permissions because belongs to Managers group auth/participation.py
