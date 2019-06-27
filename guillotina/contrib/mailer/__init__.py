# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.interfaces import IMailer
from guillotina.component import provide_utility
from guillotina.utils import import_class
import logging

logger = logging.getLogger('guillotina.contrib.mailer')

app_settings = {
    "mailer": {
        "default_sender": None,
        "endpoints": {
            "default": {
                "type": "smtp",
                "host": "localhost",
                "port": 25
            }
        },
        "debug": False,
        "utility": "guillotina.contrib.mailer.utility.MailerUtility",
        "use_html2text": True,
        "domain": None
    }
}

def includeme(root, settings):
    factory = import_class(
        settings.get('mailer', {}).get('utility',
                                       settings['mailer']['utility']))
    logger.debug(f"Setting Mail Utility: {settings['mailer']['utility']}")
    if settings['mailer']['default_sender'] is None:
        logger.warning(f"No sender mail configured on mailer.default_sender settings")
    utility = factory()
    provide_utility(utility, IMailer)

    configure.scan('guillotina.contrib.mailer.utility')
