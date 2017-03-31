# Roles

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

 * guillotina.AddContainer
 * guillotina.GetContainers
 * guillotina.DeleteContainers
 * guillotina.AccessContent
 * guillotina.GetDatabases

Anonymous user has on DB/StaticFiles/StaticDirectories/Application object :

 * guillotina.AccessContent

## Roles in guillotina container objects

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

## Container/App Roles

### guillotina.ContainerAdmin

 * guillotina.AccessContent
 * guillotina.ManageAddons
 * guillotina.RegisterConfigurations
 * guillotina.WriteConfiguration
 * guillotina.ReadConfiguration
 * guillotina.ManageCatalog

### guillotina.ContainerDeleter

 * guillotina.DeletePortal

## Default roles on Guillotina Container

They are stored in annotations using IRolePermissionMap.

Created objects set the guillotina.Owner role to the user who created it.

## Default groups on Guillotina Container

### Managers

#### RootParticipation

There is a `root` user who has permissions to all containers:

DB/APP permissions are defined on factory.py

Guillotina permissions because belongs to Managers group auth/participation.py
