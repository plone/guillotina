from plone.server.utils import strings_differ

import hashlib
import uuid
import logging


def hash_password(password, salt=None):
    if salt is None:
        salt = uuid.uuid4().hex

    if isinstance(salt, str):
        salt = salt.encode('utf-8')

    if isinstance(password, str):
        password = password.encode('utf-8')

    hashed_password = hashlib.sha512(password + salt).hexdigest()
    return '{}:{}'.format(salt.decode('utf-8'), hashed_password)


class SaltedHashPasswordChecker(object):

    def __init__(self, request):
        self.request = request

    async def validate(self, user, token):
        user_pw = getattr(user, 'password', None)
        if (not user_pw or
                ':' not in user_pw or
                'token' not in token):
            return False
        salt = user.password.split(':')[0]
        return not strings_differ(hash_password(token['token'], salt), user_pw)
