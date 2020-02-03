from guillotina import configure


app_settings = {
    "applications": ["guillotina.contrib.templates"],
    "validation_process": "guillotina.contrib.email_validation.process",
    "templates": [
        "guillotina.contrib.email_validation:templates"
    ],
    "validation_tasks": {
        "reset_password": {
            "schema": {
                "title": "Reset password validation information",
                "required": ["password"],
                "type": "object",
                "properties": {
                    "password": {
                        "type": "string",
                        "minLength": 6
                    }
                }
            },
            "executor": "guillotina.contrib.email_validation.reset_password"
        }
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.email_validation.install")
