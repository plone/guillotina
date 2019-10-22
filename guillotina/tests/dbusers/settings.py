DEFAULT_SETTINGS = {
    "auth_user_identifiers": ["guillotina.contrib.dbusers.users.DBUserIdentifier"],
    "applications": ["guillotina.contrib.dbusers"],
}

user_data = {
    "@type": "User",
    "name": "Foobar",
    "id": "foobar",
    "username": "foobar",
    "email": "foo@bar.com",
    "password": "password",
}
