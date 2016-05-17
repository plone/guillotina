# -*- encoding: utf-8 -*-
from plone.server import DICT_LANGUAGES, DICT_RENDERS


def content_negotiation(request):
    # We need to check for the language

    # We need to check for the accept
    accept = DICT_RENDERS['application/json']
    language = DICT_LANGUAGES['en']
    return accept, language
