from guillotina import configure


app_settings = {
    "applications": ["guillotina.contrib.templates"],
    "load_utilities": {
        "auth_validation": {
            "provides": "guillotina.interfaces.IAuthValidationUtility",
            "factory": "guillotina.contrib.email_validation.utility.EmailValidationUtility",
        }
    },
    "templates": ["guillotina.contrib.email_validation:templates"],
    "auth_validation_tasks": {
        "reset_password": {
            "schema": {
                "title": "Reset password validation information",
                "required": ["password"],
                "type": "object",
                "properties": {
                    "password": {
                        "type": "string",
                        "widget": "password",
                        "minLength": 6
                    }
                }
            },
            "executor": "guillotina.contrib.email_validation.reset_password",
        }
    },
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.email_validation.install")
