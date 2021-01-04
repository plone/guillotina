from guillotina import configure


app_settings = {}


def includeme(root, settings):
    configure.scan("guillotina.contrib.dyncontent.vocabularies")
    configure.scan("guillotina.contrib.dyncontent.subscriber")
