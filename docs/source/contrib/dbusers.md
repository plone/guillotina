# Guillotina dbusers

Store users/groups as content in the database for guillotina.


## Installation

- add `guillotina.contrib.dbusers` to list of applications in your guillotina configuration
- install into your container using the `@addons` endpoint using `dbusers` as id.

Available content types:

- User
- Group

### Usage

After installation, you will now have a `users` and `groups` folder
inside your container. New users can be added just like creating
content::

```json
POST /db/container/users {
    "@type": "User",
    "id": "foobar",
    "username": "@foobar",
    "name": "FooBar",
    "email": "foo@bar.com",
    "password": "foobar"
}
```

You can now authenticate with the `foobar` user.

New groups are added likewise::
```json
POST /db/container/groups {
    "@type": "Group",
    "id": "admins",
    "name": "My Site Admins",
    "description": "My site's admins group",
    "user_roles": ["guillotina.Manager"],
    "users": ["foobar", "otheradmin"],
}
```

### Management

dbusers follows the same implementation as plone_restapi for managing users

- [Plone restapi Users](https://plonerestapi.readthedocs.io/en/latest/users.html)
- [Plone restapi Groups](https://plonerestapi.readthedocs.io/en/latest/groups.html)
