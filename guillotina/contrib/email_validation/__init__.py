from guillotina import configure


app_settings = {
    "applications": ["guillotina.contrib.templates"],
    "validation_process": "guillotina.contrib.email_validation.process",
    "templates": [
        "guillotina.contrib.email_validation:templates"
    ],
    "validation_tasks": {
        "reset_password": "guillotina.contrib.email_validation.reset_password"
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.email_validation.install")
