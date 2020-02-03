from guillotina import configure
from guillotina.i18n import MessageFactory


_ = MessageFactory("guillotina.contrib.dbusers")


app_settings = {
    "auth_user_identifiers": ["guillotina.contrib.dbusers.users.DBUserIdentifier"],
    "validation_tasks": {
        "register_user": {
            "schema": {
                "title": "Register validation information",
                "required": [],
                "type": "object",
                "properties": {}
            },
            "executor": "guillotina.contrib.dbusers.register_user"
        }
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.dbusers.content.users")
    configure.scan("guillotina.contrib.dbusers.content.groups")
    configure.scan("guillotina.contrib.dbusers.install")
    configure.scan("guillotina.contrib.dbusers.services")
    configure.scan("guillotina.contrib.dbusers.subscribers")
    configure.scan("guillotina.contrib.dbusers.permissions")
    configure.scan("guillotina.contrib.dbusers.serializers")
