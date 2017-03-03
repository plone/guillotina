from guillotina import logger
from guillotina.interfaces import IDefaultLayer  # noqa


logger.warn('guillotina.api.layer.IDefaultLayer has been moved to '
            'guillotina.interfaces.IDefaultLayer. This import will '
            'no longer work in version 2.0.0 of guillotina')
