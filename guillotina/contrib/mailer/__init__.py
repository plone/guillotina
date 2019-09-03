# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.component import provide_utility
from guillotina.interfaces import IMailer
from guillotina.utils import import_class

import logging


logger = logging.getLogger("guillotina.contrib.mailer")

app_settings = {
    "mailer": {
        "default_sender": None,
        "endpoints": {"default": {"type": "smtp", "host": "localhost", "port": 25}},
        "debug": False,
        "utility": "guillotina.contrib.mailer.utility.MailerUtility",
        "use_html2text": True,
        "domain": None,
    }
}


def includeme(root, settings):
    mailer_settings = settings.get("mailer") or app_settings.get("mailer")
    factory = import_class(mailer_settings.get("utility"))
    logger.debug(f"Setting Mail Utility: {mailer_settings['utility']}")
    if settings.get("mailer", {}).get("default_sender", None) is None:
        logger.warning(f"No sender mail configured on mailer.default_sender settings")
    utility = factory()
    provide_utility(utility, IMailer)

    configure.scan("guillotina.contrib.mailer.utility")
