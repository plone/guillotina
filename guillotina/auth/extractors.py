from guillotina import jose
from guillotina._settings import app_settings

import base64
import logging


logger = logging.getLogger('guillotina')


class BasePolicy:
    name = '<FILL IN>'

    def __init__(self, request):
        self.request = request

    async def extract_token(self):
        """
        Extracts token from request.
        This will be a dictionary including something like {id, password},
        depending on the auth policy to authenticate user against
        """
        raise NotImplemented()


class BearerAuthPolicy(BasePolicy):
    name = 'bearer'

    async def extract_token(self):
        header_auth = self.request.headers.get('AUTHORIZATION')
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'bearer':
                return {
                    'type': 'bearer',
                    'token': encoded_token.strip()
                }


class WSTokenAuthPolicy(BasePolicy):
    name = 'wstoken'

    async def extract_token(self):
        request = self.request
        if 'ws_token' in request.query:
            jwt_token = request.query['ws_token'].encode('utf-8')
            try:
                jwt = jose.decrypt(
                    jose.deserialize_compact(jwt_token), app_settings['rsa']['priv'])
            except jose.Expired:
                # expired token
                logger.warn(f'Expired token {jwt_token}', exc_info=True)
                return
            except jose.Error:
                logger.warn(f'Error decrypting JWT token', exc_info=True)
                return
            data = {
                'type': 'wstoken',
                'token': jwt.claims['token']
            }
            if 'id' in jwt.claims:
                data['id'] = jwt.claims['id']
            return data


class BasicAuthPolicy(BasePolicy):
    name = 'basic'

    async def extract_token(self, value=None):
        if value is None:
            header_auth = self.request.headers.get('AUTHORIZATION')
        else:
            header_auth = value
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'basic':
                token = base64.b64decode(encoded_token).decode('utf-8')
                userid, _, password = token.partition(':')
                return {
                    'type': 'basic',
                    'id': userid.strip(),
                    'token': password.strip()
                }
