import base64
import json
import logging
import time

from guillotina.utils import get_jwk_key
from jwcrypto import jwe


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
                jwetoken = jwe.JWE()
                jwetoken.deserialize(jwt_token.decode('utf-8'))
                jwetoken.decrypt(get_jwk_key())
                payload = jwetoken.payload
            except jwe.InvalidJWEOperation:
                logger.warn(f'Invalid operation', exc_info=True)
                return
            except jwe.InvalidJWEData:
                logger.warn(f'Error decrypting JWT token', exc_info=True)
                return
            json_payload = json.loads(payload)
            if json_payload['exp'] <= int(time.time()):
                logger.warn(f'Expired token {jwt_token}', exc_info=True)
                return
            data = {
                'type': 'wstoken',
                'token': json_payload['token']
            }
            if 'id' in json_payload:
                data['id'] = json_payload['id']
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


class CookiePolicy(BasePolicy):
    name = 'cookie'

    async def extract_token(self, value=None):
        if value is None:
            token = self.request.cookies.get('auth_token')
            if token is not None:
                return {
                    'type': 'cookie',
                    'token': token.strip()
                }
