# -*- coding: utf-8 -*-
from guillotina.factory import make_app

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(threadName)10s %(name)18s: %(message)s',)

app = make_app(config_file='config.json')
