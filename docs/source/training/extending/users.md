# Users

Guillotina does not come with any user provider OOTB and is designed to be
plugged in with other services.

However, there is a simple provider that stores user data in the database
called `guillotina_dbusers` that we will use for the purpose of our training.

## Install guillotina_dbusers

Just use pip


```
pip install guillotina_dbusers
```


And add the `guillotina_dbusers` to the list of applications in your `config.yaml`.
Also make sure you are not overriding the `auth_user_identifiers` configuration
value in your `config.yaml` as `guillotina_dbusers` uses that to work.


After you restart guillotina, you can also install `dbusers`
into your container using the `@addons` endpoint:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/container/@addons HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "id": "dbusers"
    }


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "available": [
            {
                "id": "dbusers",
                "title": "Guillotina DB Users"
            },
            {
                "id": "application_name",
                "title": "Your application title"
            }
        ],
        "installed": [
            "dbusers",
            "application_name"
        ]
    }
```

## Add users

Creating users is just creating a user object.

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/container/users HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "@type": "User",
        "email": "bob@domain.io",
        "password": "secret",
        "username": "Bob"
    }


    HTTP/1.1 201 Created
    Content-Type: application/json
    Location: http://localhost:8080/db/container/users/Bob

    {
        "@id": "http://localhost:8080/db/container/users/Bob",
        "@name": "Bob",
        "@type": "User",
        "@uid": "6e6|753|05893a69ee6e4f56b540248b5728c4a4",
        "UID": "6e6|753|05893a69ee6e4f56b540248b5728c4a4"
    }
```

Logging in can be done with the `@login` endpoint which returns a jwt token.

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/container/@login HTTP/1.1
    Accept: application/json
    Authorization: Basic cm9vdDpyb290
    Content-Type: application/json
    Host: localhost:8080

    {
        "password": "secret",
        "username": "Bob"
    }


    HTTP/1.1 200 OK
    Content-Type: application/json

    {
        "exp": 1532253747,
        "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MzIyNTM3NDcsImlkIjoiQm9iIn0.1-JbNe1xNoHJgPEmJ05oULi4I9OMGBsviWFHnFPvm-I"
    }
```

Then, future requests are done with a `Bearer` token with the jwt token. For
example, to create a conversation with your user:

```eval_rst
..  http:example:: curl wget httpie python-requests

    POST /db/container/conversations/ HTTP/1.1
    Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MzIyNTM3NDcsImlkIjoiQm9iIn0.1-JbNe1xNoHJgPEmJ05oULi4I9OMGBsviWFHnFPvm-I
    Host: localhost:8080

    {
      "@type": "Conversation",
      "title": "New convo with foobar2",
      "users": ["foobar", "foobar2"]
    }
```
