# Security

Guillotina provides an imperative security system. Permissions are computed for
a given node in the resource tree using some concept we are going to describe
in this document.

## Basics

We'll be explaining the security system by showing examples.
Fist, make sure to follow the steps from
[Getting started](../narrative.html).

Now you should have a resource tree that we can represent like the following:

```
db
└── todo
    ├── <fist_todo_id>
    └── <second_todo_id>

```

Where `db` is the database, `todo` a container with to content inside.

More than that we need some users in order to be able to compute permssion(s)
for them, to do so we are going to install
[guillotina_dbusers](https://github.com/guillotinaweb/guillotina_dbusers), once
installed create two users, let's say "Bob" and "Alice". You can find more
informations about this addon especially how to get **Bearer Authorization JWT**
see [training's users section](../../training/extending/users.html).

Note that at this moment the resource tree can be represented like this:

```
db
└── todo
    ├── <fist_todo_id>
    ├── <second_todo_id>
    ├── users
    │   ├── Bob
    │   └── Alice
    └── groups

```

Now login with "Bob" and try access `/db/todo` endpoint:

```eval_rst
..  http:example:: curl wget httpie python-requests

    GET /db/todo/ HTTP/1.1
    Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MzIyNTM3NDcsImlkIjoiQm9iIn0.1-JbNe1xNoHJgPEmJ05oULi4I9OMGBsviWFHnFPvm-I
    Host: localhost:8080


    HTTP/1.1 401 Unauthorized
    Content-Type: application/json

    {
        "auths": [
            "Bob"
        ],
        "content": "< Container at /todo by 140237937521992 >",
        "reason": "You are not authorized to view"
    }
```

Like you can see in the response you are not authorized to view, and that's great
because it means that the security system works like a charm.

Let's grant "Bob" view permission for this `db/todo/` resource tree node:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/@sharing HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "prinperm": [
            {
                "permission": "guillotina.ViewContent",
                "principal": "Bob",
                "setting": "Allow"
            }
        ]
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
```

You can now access to `/db/todo` endpoint using Bob user:

```eval_rst
..  http:example:: curl wget httpie python-requests

    GET /db/todo/ HTTP/1.1
    Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MzIyNTM3NDcsImlkIjoiQm9iIn0.1-JbNe1xNoHJgPEmJ05oULi4I9OMGBsviWFHnFPvm-I
    Host: localhost:8080


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "@id": "http://localhost:8080/db/todo",
        "@name": "todo",
        "@type": "Container",
        "@uid": "6e63e13b4d1647d5a4ef5ef61ea040f1",
        "UID": "6e63e13b4d1647d5a4ef5ef61ea040f1",
        "__behaviors__": [],
        "__name__": "todo",
        "creation_date": "2018-07-22T07:33:19.098099+00:00",
        "is_folderish": true,
        "items": [
            {
                "@id": "http://localhost:8080/db/todo/9eca9e3e84ce4e79883f19fdbbe694b1",
                "@name": "9eca9e3e84ce4e79883f19fdbbe694b1",
                "@type": "ToDo",
                "@uid": "6e6|9eca9e3e84ce4e79883f19fdbbe694b1",
                "UID": "6e6|9eca9e3e84ce4e79883f19fdbbe694b1"
            },
            {
                "@id": "http://localhost:8080/db/todo/ae45417c8115463aa2d6437de3577d02",
                "@name": "ae45417c8115463aa2d6437de3577d02",
                "@type": "ToDo",
                "@uid": "6e6|ae45417c8115463aa2d6437de3577d02",
                "UID": "6e6|ae45417c8115463aa2d6437de3577d02"
            },
            {
                "@id": "http://localhost:8080/db/todo/groups",
                "@name": "groups",
                "@type": "GroupManager",
                "@uid": "6e6|ff31eda7808044488dc492d2075e4e13",
                "UID": "6e6|ff31eda7808044488dc492d2075e4e13"
            },
            {
                "@id": "http://localhost:8080/db/todo/users",
                "@name": "users",
                "@type": "UserManager",
                "@uid": "6e6|753405ce2dfe4455930c8fc850f38157",
                "UID": "6e6|753405ce2dfe4455930c8fc850f38157"
            }
        ],
        "length": 4,
        "modification_date": "2018-07-22T09:33:13.486834+00:00",
        "parent": {},
        "title": "ToDo List",
        "type_name": "Container",
        "uuid": "6e63e13b4d1647d5a4ef5ef61ea040f1"
    }
```

What we've done so far looks like we've grant user "Bob" view access to this
node, but that's not totally true.

As you can see in the permission definition we grant permission to a **principal**.
A principal is like a tag and we grant permission to that tag.
The user's id is the "principal" here but more on that later.

Another important thing is the `setting` attribute, which defined the permission
**propagation** in the resource tree, this attribute can have only three value:

- Allow: set on resource and children will inherit
- Deny: set on resource and children will inherit (good way to stop propagation)
- AllowSingle: set on resource and children will not inherit (also a good way to stop propagation)
- Unset: you remove the setting

Note that we've defined a permission with "Allow" propagation setting at this
level of the resource tree:

```
db
└── todo                   <-- permission was granted here
    ├── <fist_todo_id>
    ├── <second_todo_id>
    ├── users
    │   ├── Bob
    │   └── Alice
    └── groups

```

Which means that user "Bob" can view todo container, but also all todo, users
and groups, but cannot `db` database. Try it.

The last parameter in our permission definition we've talk so far is the
**permission** parameter itself, Guillotina provided a lot of permission by
default, you can find an exhaustive like by reading
[Guillotina permissions definitions from the source code](https://github.com/plone/guillotina/blob/master/guillotina/permissions.py).
Most of the permissions your application will need should be defined there, but
obviously you can also defined your own, more on that later.
<!-- TODO: write an "How to defined permission" section in developer. not sure exactly where ATM -->


## Groups

Groups can be assigned to users, each group names are also principals, this is
the way we can add principals to users.

Let's add a group named `todo_viewer`:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/groups HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "@type": "Group",
        "name": "todo_viewer"
    }


    HTTP/1.1 201 Created
    Content-Type: application/json
    Location: http://localhost:8080/db/todo/groups/14f624ef23094362961df0e083cd77e4

    {
        "@id": "http://localhost:8080/db/todo/groups/14f624ef23094362961df0e083cd77e4",
        "@name": "14f624ef23094362961df0e083cd77e4",
        "@type": "Group",
        "@uid": "6e6|ff3|14f624ef23094362961df0e083cd77e4",
        "UID": "6e6|ff3|14f624ef23094362961df0e083cd77e4"
    }
```

And add "Bob" and "Alice" to that group.

```eval_rst
..  http:example:: curl wget httpie python-requests

    PATCH /db/todo/users/Bob HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "user_groups": [
            "todo_viewer"
        ]
    }


    HTTP/1.1 204 No Content
    Content-Type: application/json
```

```eval_rst
..  http:example:: curl wget httpie python-requests

    PATCH /db/todo/users/Alice HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "user_groups": [
            "todo_viewer"
        ]
    }


    HTTP/1.1 204 No Content
    Content-Type: application/json
```

Let's grant `todo_viewer` view permission for this `db/todo/` resource tree node:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/@sharing HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "prinperm": [
            {
                "permission": "guillotina.ViewContent",
                "principal": "todo_viewer",
                "setting": "Allow"
            }
        ]
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
```

Now alice should be able to view todo container and all it's children.

At the moment alice can view users and groups which is not convenient for a
`todo_viewer` group, let's deny that.

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/users/@sharing HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "prinperm": [
            {
                "permission": "guillotina.ViewContent",
                "principal": "todo_viewer",
                "setting": "Deny"
            }
        ]
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
```

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/groups/@sharing HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "prinperm": [
            {
                "permission": "guillotina.ViewContent",
                "principal": "todo_viewer",
                "setting": "Deny"
            }
        ]
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
```

Now both Alice and Bob can't access to users and groups, if you want Bob to be
able to access those endpoints you should explicitly set permission for
principal "Bob" on those ones.

## Roles

Roles are granted permissions, which means that a principal with one role will
inherit all that role permissions.

Guillotina defined serval default roles, see
[developer roles section](../../developer/roles.html). But remember that you
can defined your own ones(more on that later).
<!-- TODO: write an "How to defined role" section in developer/role.md -->

For example let's give to principal "Alice" the `guillotina.Editor` role on 
`/db/todo/<first_todo_id>` resource tree node, which
grants the following permissions:

- guillotina.AccessContent
- guillotina.ViewContent
- guillotina.ModifyContent
- guillotina.ReindexContent

To do use run (don't forget to replace `<first_todo_id_>` with your first todo
id):

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/<first_todo_id>/@sharing HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "prinrole": [
            {
                "principal": "Alice",
                "role": "guillotina.Editor",
                "setting": "Allow"
            }
        ]
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
```

Now Alice can access, view, modify and reindex the first todo but Bob still only
view to it.

You can also add permission for a role at/from a given resource tree node for
a given role, for example at the moment principal "Alice" which have
"guillotina.Editor" role on `/db/todo/<first_todo_id>` cannot delete it.

Let's fix that by giving "guillotina.DeleteContent" permission to
"guillotina.Editor" role at this specific resource tree node:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/todo/<first_todo_id>/@sharing HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "roleperm": [
            {
                "permission": "guillotina.DeleteContent",
                "role": "guillotina.Editor",
                "setting": "Allow"
            }
        ]
    }


    HTTP/1.1 200 OK
    Content-Type: application/json
```

Now anyone who have "guillotina.Editor" role on that node, including only Alice
at the moment, will be able to delete it.

## Security Levels

Security for every operation is managed against three definitions (in order of priority):

+ Local
+ Global
+ Code

"Local" means for a given resource tree node.

"Global" stand for application level.

And finally "Code" for code level, like services, containers or whatever code
exposed to the API.

This means that principal or role could be mandatory to acces them.

Locals can defined:

- Permission for principal with propagation definition
- Role for principal with propagation definition
- Permission for role with propagation definition

Globals:

- Role for principal
- Permission for principal

Code:

- Role for principal
- Permission for principal
- Permission for role

### Roles

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

## REST APIs

### Get all the endpoints and their security

`[GET] APPLICATION_URL/@apidefinition` (you need `guillotina.GetContainers` permission)

### Get the security info for a resource (with inherited info)

`[GET] RESOURCE/@sharing` (you need `guillotina.SeePermissions` permission)

### Modify the local roles/permission for a resource

`[POST] RESOURCE/@sharing` (you need `guillotina.ChangePermissions` permission)

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

### Propagation setting

The different types are:

- Allow: set on resource and children will inherit
- Deny: set on resource and children will inherit (good way to stop propagation)
- AllowSingle: set on resource and children will not inherit (also a good way to stop propagation)
- Unset: you remove the setting
