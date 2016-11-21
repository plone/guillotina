from plone.server import app_settings
from plone.server import jose


class BasePolicy(object):

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
    async def extract_token(self):
        header_auth = self.request.headers.get('AUTHORIZATION')
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'basic' or schema.lower() == 'bearer':
                return {
                    'password': encoded_token
                }


class WSTokenAuthPolicy(BasePolicy):
    async def extract_token(self):
        request = self.request
        if 'ws_token' in request.GET:
            jwt_token = request.GET['ws_token'].encode('utf-8')
            request.GET['ws_token'].encode('utf-8')
            jwt = jose.decrypt(
                jose.deserialize_compact(jwt_token), app_settings['rsa']['priv'])
            return {
                'password': jwt.claims['token']
            }


class BasicAuthPolicy(BasePolicy):
    async def extract_token(self):
        header_auth = self.request.headers.get('AUTHORIZATION')
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'basic' or schema.lower() == 'bearer':
                userid, _, password = encoded_token.partition(':')
                return {
                    'id': userid,
                    'password': password
                }


class JWTAuthPolicy(BasePolicy):
    pass
