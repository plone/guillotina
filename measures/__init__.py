# make this an application so we can load configuration to run with these
from guillotina import configure


app_settings = {}


def includeme():
    configure.scan("measures.configuration")
