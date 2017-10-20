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

```
POST /db/container/@addons
{
  "id": "dbusers"
}
```

## Add users

Creating users is just creating a user object.

```
POST /db/container/users
{
  "@type": "User", "username": "foobar", "email": "foo@bar.com", "password": "foobar"
}
```

Logging in can be done with the `@login` endpoint which returns a jwt token.

```
POST /db/container/@login
{
  "username": "foobar", "password": "foobar"
}
```


Then, future requests are done with a `Bearer` token with the jwt token. For
example, to create a conversation with your user:

```
POST /db/container/conversations
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE1MDgwMTU0OTcsImlkIjoiZm9vYmFyIn0.vC6HHuLmcf8d1I7RpOTxAeHQDfMRjsOoBS-xH4Q1sdw
{
  "@type": "Conversation",
  "title": "New convo with foobar2",
  "users": ["foobar", "foobar2"]
}
```
