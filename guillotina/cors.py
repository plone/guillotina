from aiohttp.web_exceptions import HTTPUnauthorized
from guillotina import app_settings
from guillotina import glogging
from guillotina.interfaces import IRequest

import fnmatch


logger = glogging.getLogger('guillotina')


class DefaultCorsRenderer:

    def __init__(self, request: IRequest):
        self.request = request

    async def get_settings(self):
        return app_settings['cors']

    async def get_headers(self):
        settings = await self.get_settings()
        headers = {}
        origin = self.request.headers.get('Origin', None)
        if origin:
            if not any([fnmatch.fnmatchcase(origin, o)
                        for o in settings['allow_origin']]):
                logger.error('Origin %s not allowed' % origin, request=self.request)
                raise HTTPUnauthorized()
            elif self.request.headers.get('Access-Control-Allow-Credentials', False):
                headers['Access-Control-Allow-Origin', origin]
            else:
                if any([o == "*" for o in settings['allow_origin']]):
                    headers['Access-Control-Allow-Origin'] = '*'
                else:
                    headers['Access-Control-Allow-Origin'] = origin
        if self.request.headers.get(
                'Access-Control-Request-Method', None) != 'OPTIONS':
            if settings['allow_credentials']:
                headers['Access-Control-Allow-Credentials'] = 'True'
            if len(settings['allow_headers']):
                headers['Access-Control-Expose-Headers'] = \
                    ', '.join(settings['allow_headers'])
        return headers
