# Guillotina dbusers

Store users/groups as content in the database for Guillotina.

## Installation

- add `guillotina.contrib.dbusers` to list of applications in your Guillotina configuration
- install into your container using the `@addons` endpoint using `dbusers` as id.

Available content types:

- User
- Group

### Usage

After installation, you will now have a `users` and `groups` folder
inside your container.

Guillotina users holding `guillotina.ContainerAdmin` or
`guillotina.Manager` permissions can add new users like

```text
POST /db/container/users {
    "@type": "User",
    "id": "foobar",
    "username": "@foobar",
    "name": "FooBar",
    "email": "foo@bar.com",
    "password": "foobar",
    "user_roles": ["guillotina.Member"]
}
```

You can now login to the container with the `foobar` user.

New groups are added likewise

```text
POST /db/container/groups {
    "@type": "Group",
    "id": "admins",
    "name": "My Site Admins",
    "description": "My site's admins group",
    "user_roles": ["guillotina.Manager"],
    "users": ["foobar", "otheradmin"]
}
```

### Management

dbusers follows the same implementation as [plone.restapi](https://6.docs.plone.org/plone.restapi/docs/source/) for managing users

- [Plone REST API Users](https://6.docs.plone.org/plone.restapi/docs/source/endpoints/users.html)
- [Plone REST API Groups](https://6.docs.plone.org/plone.restapi/docs/source/endpoints/groups.html)
