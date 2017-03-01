from guillotina.interfaces import IDefaultLayer  # noqa
from guillotina import logger

logger.warn('guillotina.api.layer.IDefaultLayer has been moved to '
            'guillotina.interfaces.IDefaultLayer. This import will '
            'no longer work in version 2.0.0 of guillotina')
