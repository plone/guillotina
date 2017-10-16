# -*- encoding: utf-8 -*-

# load the patch before anything else.
from guillotina import glogging
from guillotina import patch  # noqa
from guillotina._cache import BEHAVIOR_CACHE  # noqa
from guillotina._cache import FACTORY_CACHE  # noqa
from guillotina._cache import PERMISSIONS_CACHE  # noqa
from guillotina._cache import SCHEMA_CACHE  # noqa
from guillotina._settings import app_settings  # noqa
from guillotina.i18n import default_message_factory as _  # noqa
from zope.interface import Interface  # noqa


# create logging
logger = glogging.getLogger('guillotina')
