from guillotina import configure


app_settings = {
    "load_utilities": {
        "audit": {
            "provides": "guillotina.contrib.audit.interfaces.IAuditUtility",
            "factory": "guillotina.contrib.audit.utility.AuditUtility",
            "settings": {"index_name": "audit"},
        }
    }
}


def includeme(root, settings):
    configure.scan("guillotina.contrib.audit.install")
    configure.scan("guillotina.contrib.audit.utility")
    configure.scan("guillotina.contrib.audit.subscriber")
    configure.scan("guillotina.contrib.audit.api")
