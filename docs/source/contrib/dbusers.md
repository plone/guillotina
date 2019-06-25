
# Guillotina dbusers

Store users/groups in the database for guillotina.


## Installation

- add `guillotina.contrib.dbusers` to list of applications in your guillotina configuration
- install into your container using the `@addons` endpoint using `dbusers` as id.

Available content types:
- User
- Group

### Usage

After installation, you will now have a `users` and `groups` folder inside
your container::

```json
POST /db/container/users {
    "@type": "User",
    "username": "foobar",
    "email": "foo@bar.com",
    "password": "foobar"
}
```


You can now authenticate with the `foobar` user.


### Login

Besides using default authentication mechanisms, this package also provides
a `@login` so you can work with jwt tokens::

```json
POST /db/container/@login {
    "username": "foobar",
    "password": "foobar"
}
```


And a `@refresh_token` endpoint:L

```json
POST /db/container/@refresh_token
```


### Management

dbusers follows the same implementation as plone_restapi for managing users

- [Plone restapi Users](https://plonerestapi.readthedocs.io/en/latest/users.html)
- [Plone restapi Groups](https://plonerestapi.readthedocs.io/en/latest/groups.html)
