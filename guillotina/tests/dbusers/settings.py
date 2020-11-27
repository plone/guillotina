DEFAULT_SETTINGS = {
    "auth_user_identifiers": ["guillotina.contrib.dbusers.users.DBUserIdentifier"],
    "applications": ["guillotina.contrib.dbusers"],
}

FAKE_RECAPTCHA = "FAKE_RECAPTCHA"

DEFAULT_REGISTRATION_SETTINGS = {
    "auth_user_identifiers": ["guillotina.contrib.dbusers.users.DBUserIdentifier"],
    "applications": [
        "guillotina.contrib.dbusers",
        "guillotina.contrib.mailer",
        "guillotina.contrib.email_validation",
    ],
    "mailer": {"utility": "guillotina.contrib.mailer.utility.TestMailerUtility"},
    "allow_register": True,
    "datetime_format": "%m/%d/%Y, MYTIMEFORMAT %H:%M:%S",
    "_fake_recaptcha_": "FAKE_RECAPTCHA",
}

user_data = {
    "@type": "User",
    "name": "Foobar",
    "id": "foobar",
    "username": "foobar",
    "email": "foo@bar.com",
    "password": "password",
}
