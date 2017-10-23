# Security

Security for every operation is managed against three definitions (in order of priority):

+ Local
+ Global
+ Code

Locally can be defined:

* A user/group has a permission in this object but not children
* A user/group has a permission in this object and it's children
* A user/group has is forbidden permission in this object and its children

* A user/group has a role on this object but not it's children
* A user/group has a role on this object and it's children
* A user/group has is forbidden a role on this object and its children

* A role has a permission on this object and its children
* A role has a permission on this object and its children
* A role has is forbidden permission in this object and its children


Globally:

* A user/group has this Role
* A user/group has this Permission

Code:

* A user/group has this Role
* A user/group has this permission
* A role has this permission


## Roles

There are two kind of roles: Global and Local. The ones that are defined to be local
can't be used globally and vice-versa. On indexing, the global roles are the ones
that are indexed for security in addition to the flat user/group information from each resource.


## Python helper functions

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

## REST APIS

### Get all the endpoints and its security

[GET] APPLICATION_URL/@apidefinition (you need guillotina.GetContainers permission)

### Get the security info for a resource (with inherited info)

[GET] RESOURCE/@sharing (you need guillotina.SeePermissions permission)

### Modify the local roles/permission for a resource

[POST] RESOURCE/@sharing (you need guillotina.ChangePermissions permission)

```json
{
"prinperm": [
  {
    "principal": "foobar",
    "permission": "guillotina.ModifyContent",
    "setting": "Allow"
  }
],
"prinrole": [
  {
    "principal": "foobar",
    "role": "guillotina.Owner",
    "setting": "Allow"
  }
],
"roleperm": [
  {
    "permission": "guillotina.ModifyContent",
    "role": "guillotina.Member",
    "setting": "Allow"
  }
]
}
```

The different type of types are :

- Allow : you set it on the resource and the children will inherit
- Deny : you set in on the resource and the children will inherit
- AllowSingle : you set in on the resource and the children will not inherit
- Unset : you remove the setting
