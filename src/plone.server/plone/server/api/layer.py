from plone.server.interfaces import IDefaultLayer  # noqa
import logging


logger = logging.getLogger('plone.server')
logger.warn('plone.server.api.layer.IDefaultLayer has been moved to '
            'plone.server.interfaces.IDefaultLayer. This import will '
            'no longer work in version 2.0.0 of plone.server')
