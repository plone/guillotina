from guillotina import configure

app_settings = {
    "load_utilities": {
        "template": {
            "provides": "guillotina.contrib.templates.interfaces.IJinjaUtility",
            "factory": "guillotina.contrib.templates.utility.JinjaUtility",
        }
    },
    "templates": [],
    "template_content_type": False
}



def includeme(root, settings):
    if settings.get('template_content_type', False):
        configure.scan("guillotina.contrib.templates.content")


