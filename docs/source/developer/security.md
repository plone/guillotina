# Security

Security information for every operation is checked against three informations:

* Code definitions
* Local definitions
* Global definitions

Order or priority :

+ Local
+ Global
+ Code

Locally can be defined :

* A user/group has a permission in this object and its not inherit
* A user/group has a permission in this object and its going to be inherit
* A user/group has a forbitten permission in this object and its inherit

* A user/group has a role in this object and its not inherit
* A user/group has a role in this object and its inherit
* A user/group has a forbitten role in this object and its inherit

* A role has a permission in this object and its not inherit
* A role has a permission in this object and its inherit
* A role has a forbitten permission in this object and its inherit


Globally :

* This user/group has this Role
* This user/group has this Permission

Code :

* This user/group has this Role
* This user/group has this permission
* This role has this permission

# Roles

There is two kind of roles : Global and Local. Ones that are defined to be local
can't be used globally and viceversa. On indexing the global roles are the ones
that are indexed for security plus the flat user/group information from each resource.

# Python helper functions

```python

# Code to get the global roles that have access_content to an object
from guillotina.security.utils import get_roles_with_access_content
get_roles_with_access_content(obj)

# Code to get the user list that have access content to an object
from guillotina.security.utils import get_principals_with_access_content
get_principals_with_access_content(obj)


# Code to get all the security info
from guillotina.security.utils import settings_for_object
settings_for_object(obj)

# Code to get the Interaction object ( security object )
from guillotina.interfaces import IInteraction

interaction = IInteraction(request)

# Get the list of global roles for a user and some groups
interaction.global_principal_roles(principal, groups)

# Get if the authenticated user has permission on a object
interaction.check_permission(permission, obj)
```

# REST APIS

## Get all the endpoints and its security

[GET] APPLICATION_URL/@apidefinition (you need guillotina.GetContainers permission)

## Get the security info for a resource (with inherited info)

[GET] RESOURCE/@sharing (you need guillotina.SeePermissions permission)

## Modify the local roles/permission for a resource

[POST] RESOURCE/@sharing (you need guillotina.ChangePermissions permission)

```json
  {
    "type": "Allow",
    "prinrole": {
      "principal_id": ["role1", "role2"]
    },
    "prinperm": {
      "principal_id": ["perm1", "perm2"]
    },
    "roleperm": {
      "role1": ["perm1", "perm2"]
    }
  }
```

The different type of types are :

- Allow : you set it on the resource and the childs will inherit
- Deny : you set in on the resource and the childs will inherit
- AllowSingle : you set in on the resource and the childs will not inherit
- Unset : you remove the setting
