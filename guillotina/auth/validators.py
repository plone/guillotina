import hashlib
import logging
import uuid

import jwt
from guillotina import configure
from guillotina._settings import app_settings
from guillotina.auth import find_user
from guillotina.component import get_utility
from guillotina.component import query_utility
from guillotina.interfaces import IPasswordChecker
from guillotina.interfaces import IPasswordHasher
from guillotina.utils import strings_differ


logger = logging.getLogger('guillotina')

class BaseValidator(object):
    for_validators = None

    def __init__(self, request):
        self.request = request


@configure.utility(provides=IPasswordHasher, name='sha512')
def sha512_pw_hasher(pw, salt):
    return hashlib.sha512(pw + salt).hexdigest()


@configure.utility(provides=IPasswordChecker, name='sha512')
def hash_password_checker(token, password):
    split = token.split(':')
    if len(split) != 3:
        return False
    algorithm = split[0]
    salt = split[1]
    return not strings_differ(hash_password(password, salt, algorithm), token)


def hash_password(password, salt=None, algorithm='sha512'):
    if salt is None:
        salt = uuid.uuid4().hex

    if isinstance(salt, str):
        salt = salt.encode('utf-8')

    if isinstance(password, str):
        password = password.encode('utf-8')

    hash_func = get_utility(IPasswordHasher, name=algorithm)
    hashed_password = hash_func(password, salt)
    return '{}:{}:{}'.format(algorithm, salt.decode('utf-8'), hashed_password)


def check_password(token, password):
    split = token.split(':')
    if len(split) != 3:
        return False
    algorithm = split[0]
    check_func = query_utility(IPasswordChecker, name=algorithm)
    if check_func is None:
        logger.error(f'Could not find password checker for {algorithm}')
        return False
    return check_func(token, password)


class SaltedHashPasswordValidator(object):
    for_validators = ('basic', 'wstoken')

    def __init__(self, request):
        self.request = request

    async def validate(self, token):
        user = await find_user(self.request, token)
        user_pw = getattr(user, 'password', None)
        if (not user_pw or
                ':' not in user_pw or
                'token' not in token):
            return
        if check_password(user_pw, token['token']):
            return user


class JWTValidator(object):
    for_validators = ('bearer', 'wstoken', 'cookie')

    def __init__(self, request):
        self.request = request

    async def validate(self, token):
        if token.get('type') not in ('bearer', 'wstoken', 'cookie'):
            return

        if '.' not in token.get('token', ''):
            # quick way to check if actually might be jwt
            return

        try:
            validated_jwt = jwt.decode(
                token['token'],
                app_settings['jwt']['secret'],
                algorithms=[app_settings['jwt']['algorithm']])
            token['id'] = validated_jwt['id']
            token['decoded'] = validated_jwt
            user = await find_user(self.request, token)
            if user is not None and user.id == token['id']:
                return user
        except (jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError,
                KeyError):
            pass

        return
