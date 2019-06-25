# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.interfaces import IMailer
from guillotina.component import provide_utility
from guillotina.utils import import_class


app_settings = {
    "mailer": {
        "default_sender": "foo@bar.com",
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
                                       app_settings['mailer']['utility']))
    utility = factory()
    provide_utility(utility, IMailer)

    configure.scan('guillotina.contrib.mailer.utility')
