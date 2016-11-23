from plone.server.utils import strings_differ
from plone.server import app_settings
from plone.server.auth import find_user
import jwt

import hashlib
import uuid


class BaseValidator(object):
    def __init__(self, request):
        self.request = request


def hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex

    if isinstance(salt, str):
        salt = salt.encode('utf-8')

    if isinstance(password, str):
        password = password.encode('utf-8')

    hashed_password = hashlib.sha512(password + salt).hexdigest()
    return '{}:{}'.format(salt.decode('utf-8'), hashed_password)


class SaltedHashPasswordValidator(object):

    def __init__(self, request):
        self.request = request

    async def validate(self, token):
        user = await find_user(self.request, token)
        user_pw = getattr(user, 'password', None)
        if (not user_pw or
                ':' not in user_pw or
                'token' not in token):
            return False
        salt = user.password.split(':')[0]
        if not strings_differ(hash_password(token['token'], salt), user_pw):
            return user


class JWTValidator(object):
    def __init__(self, request):
        self.request = request

    async def validate(self, token):
        if token.get('type') != 'bearer':
            return False

        if '.' not in token.get('token', ''):
            # quick way to check if actually might be jwt
            return False

        try:
            validated_jwt = jwt.decode(
                token['token'],
                app_settings['jwt']['secret'],
                algorithms=[app_settings['jwt']['algorithm']])
            token['id'] = validated_jwt['id']
            user = await find_user(self.request, token)
            if user and user.id == token['id']:
                return user
        except jwt.exceptions.DecodeError:
            pass

        return False
